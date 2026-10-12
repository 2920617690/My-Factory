"""Official SDK bridge in the existing dedicated VM, without the B HTTP server."""
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
from uuid import uuid4
from .errors import RuntimeFault, sanitize
from .protocol import CapabilityRef


class OfficialHarnessAdapter:
    def __init__(self, config, source_fixture, evidence_dir):
        self.config, self.source_fixture = config, source_fixture
        self.evidence_dir = Path(evidence_dir)
        self._lock = threading.Lock()

    def run(self, request, snapshot, arguments, expected, trace):
        import hashlib
        cfg = self.config
        if not cfg.get('enabled', False):
            raise RuntimeFault('HARNESS_NOT_CONFIGURED', 'RUNTIME_ERROR', '官方 Harness 尚未配置；未调用模型')
        if not self._lock.acquire(blocking=False):
            raise RuntimeFault('HARNESS_BUSY', 'RUNTIME_ERROR', '官方运行环境正在执行另一个请求')
        entry = trace.start(request.capability, 'mf.harness.adapter', '0.1.0', {'execution_mode':'official_harness_vm'})
        try:
            if 'order_id' not in arguments and 'order_ids' not in arguments:
                raise RuntimeFault('HARNESS_SCOPE_UNSUPPORTED', 'VALIDATION', '现有真实模型路径支持订单或订单组核对')
            root = json.loads(self.source_fixture.read_text())
            original = next((r for r in root['scenarios'] if r['snapshot_id'] == snapshot['snapshot_id']), None)
            if original != snapshot:
                raise RuntimeFault('HARNESS_CONTEXT_MISMATCH', 'VALIDATION', '当前受控 Harness 使用固定模拟来源，传入事实与该来源不一致')
            env = {**os.environ, 'LIMA_HOME':cfg['lima_home']}
            prefix = [cfg['lima_bin'], 'shell', cfg['vm_name'], 'sudo', '-u', 'mf-agent']
            guest_hash = subprocess.run(prefix + ['sha256sum', '/opt/mf-demo/fixtures/factory.json'],
                text=True, capture_output=True, timeout=15, env=env, check=True).stdout.split()[0]
            if guest_hash != hashlib.sha256(self.source_fixture.read_bytes()).hexdigest():
                raise RuntimeFault('HARNESS_SOURCE_MISMATCH', 'RUNTIME_ERROR', '来宾与 Runtime 模拟来源摘要不一致')
            upstream_id = 'MF-DEMO-'+uuid4().hex
            body = {'task_id':upstream_id, 'snapshot_id':snapshot['snapshot_id'], **arguments,
                'question':request.parameters.get('question', '查询库存并核对所选订单需求，说明短缺与备料条件。')}
            command = prefix + ['/usr/bin/env', '-C', '/home/mf-agent', '/usr/bin/timeout', '--signal=TERM',
                '--kill-after=5', '180s', '/home/mf-agent/.venv/bin/python', '/opt/mf-demo/guest_run.py']
            messages = self._execute(command, body, env, request.policy.timeout_seconds)
            complete = next((m['data'] for m in messages if m['kind'] == 'completed'), None)
            if complete is None:
                raise RuntimeFault('HARNESS_RUN_FAILED', 'RUNTIME_ERROR', '官方模型回合未完成')
            audits = complete['audit']
            matching = [a for a in audits if a['name']=='factory_shortage_analyze' and a['arguments']==arguments
                        and not a['result']['isError']]
            reads = [a for a in audits if a['name']=='factory_inventory_query' and not a['result']['isError']]
            if not matching or not reads or matching[-1]['result']['value'] != expected:
                raise RuntimeFault('HARNESS_TOOL_MISMATCH', 'RUNTIME_ERROR', '实际工具返回未通过请求与确定性结果核对')
            for audit in audits:
                tool = trace.start(CapabilityRef(capability_id='inventory.query' if audit['name']=='factory_inventory_query' else 'inventory.analyze', version='1.0.0'),
                    'mf.inventory.mock', '0.3.0', {'native_tool_name':audit['name'], 'tool_call_id':audit['call_id'], 'arguments':audit['arguments']})
                # Guest audit supplies result time; receipt is not a reconstructed start timestamp.
                tool.attributes['guest_result_at'] = audit['at']
                tool.attributes['timing_source'] = 'host_receipt_interval'
                trace.finish(tool, audit['result'])
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
            evidence_name = 'official-'+upstream_id+'.json'
            raw = {'task_id':request.task_id,'execution_id':request.execution_id,'upstream_session_id':upstream_id,
                   'source_sha256':guest_hash,'messages':messages}
            (self.evidence_dir/evidence_name).write_text(json.dumps(sanitize(raw), ensure_ascii=False, indent=2)+'\n')
            output = {'analysis':matching[-1]['result']['value'], 'narrative':complete['final_response'],
                'evidence':{'execution_mode':'brain', 'provider':'DeepSeek 官方 API', 'model':complete['model'],
                            'tool_calls':len(audits), 'verified':True, 'record':evidence_name}}
            trace.finish(entry, {'verified':True,'tool_calls':len(audits),'record':evidence_name})
            return output
        except RuntimeFault as fault:
            trace.finish(entry, error=fault.envelope(request, entry.trace_id))
            raise
        except Exception as error:
            fault = RuntimeFault('HARNESS_CONNECTION_FAILED', 'RUNTIME_ERROR', '官方运行环境连接或执行失败', {'exception_type':type(error).__name__})
            trace.finish(entry, error=fault.envelope(request, entry.trace_id))
            raise fault from error
        finally:
            self._lock.release()

    @staticmethod
    def _execute(command, body, env, timeout):
        messages, inbox = [], queue.Queue()
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, env=env, start_new_session=True) as process:
            def read():
                for line in process.stdout:
                    inbox.put(line)
                inbox.put(None)
            thread = threading.Thread(target=read, daemon=True)
            thread.start()
            process.stdin.write(json.dumps(body, ensure_ascii=False))
            process.stdin.close()
            end = time.monotonic()+timeout
            try:
                size = 0
                while True:
                    remaining = end-time.monotonic()
                    if remaining <= 0: raise RuntimeFault('EXECUTION_TIMEOUT', 'RUNTIME_ERROR', '模型执行超过运行时限')
                    try: line = inbox.get(timeout=min(remaining, 0.5))
                    except queue.Empty: continue
                    if line is None: break
                    size += len(line)
                    if size > 2_000_000: raise RuntimeFault('HARNESS_OUTPUT_TOO_LARGE', 'RUNTIME_ERROR', '模型事件超过接收上限')
                    message = sanitize(json.loads(line))
                    messages.append(message)
                    if message['kind']=='failed':
                        raise RuntimeFault('HARNESS_RUN_FAILED', 'RUNTIME_ERROR', '官方 SDK 报告本次执行失败', {'upstream_error_type':message['data'].get('error')})
                if process.wait(timeout=5)!=0: raise RuntimeFault('HARNESS_RUN_FAILED','RUNTIME_ERROR','官方运行进程未正常结束')
                return messages
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try: process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
