"""Official SDK bridge inside the mf-agent VM identity; JSONL to the local UI."""
import dataclasses
import hashlib
import importlib.metadata
import json
import os
import re
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from deepseek_harness import DeepSeekHarness

ROOT = Path('/opt/mf-demo')
STATE = Path.home() / 'mf-demo'
for path in [STATE, STATE/'runs', STATE/'workspace', STATE/'dsh']:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)


def redact(value):
    text = json.dumps(value, ensure_ascii=False, default=str)
    key = os.environ.get('DEEPSEEK_API_KEY')
    if key:
        text = text.replace(key, '[REDACTED]')
    return json.loads(re.sub(r'sk-[A-Za-z0-9_-]{12,}', '[REDACTED]', text))


def emit(kind, value):
    print(json.dumps(redact({'kind': kind, 'at': datetime.now(timezone.utc).isoformat(), 'data': value}), ensure_ascii=False), flush=True)


def terminate(_signal, _frame):
    raise TimeoutError('模型回合达到运行时限，已停止')


def main():
    signal.signal(signal.SIGTERM, terminate)
    cfg = Path.home()/'.env.mf-demo'
    if not cfg.is_file() or cfg.stat().st_mode & 0o077:
        raise RuntimeError('请先配置来宾的私有模型凭据')
    for line in cfg.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            if key in ['DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'MF_MODEL']:
                os.environ[key] = value.strip()
    if not os.environ.get('DEEPSEEK_API_KEY'):
        raise RuntimeError('模型密钥尚未配置')
    request = json.loads(sys.stdin.read(16384))
    task_id = request['task_id']
    if not re.fullmatch(r'MF-DEMO-[a-f0-9]{32}', task_id):
        raise ValueError('非法任务编号')
    snapshots = {s['snapshot_id']: s for s in json.loads((ROOT/'fixtures/factory.json').read_text())['scenarios']}
    if request['snapshot_id'] not in snapshots:
        raise ValueError('非法数据截面')
    ids = request.get('order_ids')
    selected = {'order_ids': ids} if ids is not None else {'order_id': request.get('order_id')}
    valid_ids = {o['order_id'] for o in snapshots[request['snapshot_id']]['orders']}
    if ids is not None:
        if (not isinstance(ids, list) or not 2 <= len(ids) <= 5 or any(not isinstance(id, str) for id in ids)
            or len(set(ids)) != len(ids) or any(id not in valid_ids for id in ids) or request.get('order_id') is not None):
            raise ValueError('非法订单组')
    elif request.get('order_id') not in valid_ids:
        raise ValueError('非法订单')
    installed = STATE/'dsh/profiles/sdk-minimal/node_modules/@my-factory/factory-demo-tools'
    for name in ['index.mjs', 'business.mjs']:
        if hashlib.sha256((installed/'src'/name).read_bytes()).digest() != hashlib.sha256((ROOT/'factory-tools/src'/name).read_bytes()).digest():
            raise RuntimeError('已安装插件与演示源码不一致，请更新官方 profile 插件后再运行')
    run_dir = STATE/'runs'/task_id
    run_dir.mkdir(mode=0o700)
    patch = run_dir/'factory.patch.yml'
    patch.write_text(
        '- id: session-log-deepseek\n  config:\n    enabled: false\n'
        '- id: plugin-package-inventory-deepseek\n  config:\n    enabled: false\n'
        '- id: persistent-bash\n  disabled: true\n- id: persistent-pwsh\n  disabled: true\n'
        '- insert:\n    - id: factory-demo-tools\n      name: "@my-factory/factory-demo-tools"\n      config:\n'
        f'        fixturePath: {ROOT}/fixtures/factory.json\n'
        f'        snapshotId: {request["snapshot_id"]}\n'
        f'        auditPath: {run_dir}/tool-audit.jsonl\n'
        f'        registryPath: {run_dir}/registry.json\n')
    prompt = (f'当前演示截面为 {request["snapshot_id"]}，工厂 FACTORY-001，所选范围 {json.dumps(selected, ensure_ascii=False)}。\n'
        f'用户请求：{request["question"]}\n'
        '请必须先实际调用 factory_inventory_query(material_id="*") 读取批次、预留、待检、楼层事实，'
        f'再实际调用 factory_shortage_analyze，参数严格使用 {json.dumps(selected)}，取得完整BOM检查结果。'
        '回答使用简明中文，先说订单是否齐套，再说明短缺数量、在途是否可计入以及二层备料差异。'
        '单订单是独立核对；订单组必须把共同物料需求合并，只计一次共享库存，解释逐单满足是否仍有共同缺口。'
        '结合business_events解释部分收货与质量放行，采购quantity为尚未收货量，received_quantity已计入批次，不能再加一次。'
        '如transfer_blocked为true，明确跨层备料受阻，不得说可以立即搬运。'
        '不要自行分配库存、生成最优排产或承诺运输时间。不要输出表格，最多6条要点。'
        '使用工厂人员易读的业务语言，不输出feasible、line_ready等内部字段，控制在600中文字以内。'
        '需求量和可用量必须分别使用工具的demand和available原始值；不可将需求量充当可用量。'
        '库存满足不等于准时交付；所有数量判断以工具事实为准。'
        '如用户要求修改库存或下发设备指令，明确拒绝写入，可完成只读分析。')
    harness = DeepSeekHarness(provider='deepseek-official', model=os.environ.get('MF_MODEL','deepseek-flash'),
        max_tokens=4096, cwd=str(STATE/'workspace'), runtime_cwd=str(STATE/'workspace'),
        dsh_home=str(STATE/'dsh'), profile='sdk-minimal', patches=(str(patch),),
        initialize_timeout_seconds=40, request_timeout_seconds=150,
        env={'DSH_SYSTEM_PROMPT': '你是My Factory工厂大脑，使用已注册只读工具核实模拟ERP/WMS事实。只有两项只读工具；不写库存，不执行命令，不下发AGV。所有方案均待企业授权。'})
    try:
        with harness:
            emit('ready', {'session_id': task_id, 'model': os.environ.get('MF_MODEL','deepseek-flash'),
                'sdk': importlib.metadata.version('deepseek-harness-sdk'), 'snapshot_id': request['snapshot_id']})
            def notification(item):
                if item.method == 'session.event':
                    event = item.payload.get('event', {})
                    if event.get('type') in ['request/header', 'tool/call', 'tool/result', 'turn/end']:
                        emit('session_event', event)
            result = harness.run(prompt, session_id=task_id, on_notification=notification)
            value = redact(dataclasses.asdict(result))
            (run_dir/'sdk-result.json').write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
            if result.finish_reason != 'completed':
                raise RuntimeError(f'真实模型回合未完成：{result.finish_reason}')
            calls = [event for event in result.events if event['type'] == 'tool/call']
            if not {'factory_inventory_query','factory_shortage_analyze'}.issubset({c['data']['name'] for c in calls}):
                raise RuntimeError('模型未取得两项真实工具调用证据')
            emit('completed', {'final_response': result.final_response, 'finish_reason': result.finish_reason,
                'session_id': task_id, 'model': os.environ.get('MF_MODEL','deepseek-flash'), 'events': result.events,
                'registry': json.loads((run_dir/'registry.json').read_text()),
                'audit': [json.loads(line) for line in (run_dir/'tool-audit.jsonl').read_text().splitlines()]})
    finally:
        harness.close()


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        emit('failed', {'error': type(error).__name__, 'message': str(error)})
        sys.exit(1)
