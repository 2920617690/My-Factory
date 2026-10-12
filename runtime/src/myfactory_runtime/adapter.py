"""Synchronous RuntimeClient API. Execution facts are ephemeral; tasks live upstream."""
import hashlib
import json
import re
import threading
from copy import deepcopy
from pydantic import ValidationError
from .errors import RuntimeFault
from .protocol import CapabilityRef, EntityRef, ExecutionRequest, ExecutionResult
from .registry import ExecutionTrace


class MyFactoryRuntimeAdapter:
    def __init__(self, registry):
        self.registry = registry
        self._records, self._lock = {}, threading.Lock()

    def get_capabilities(self):
        return {'schema_version':'mf.execution.v1','capabilities':self.registry.discover(),
                'execution_modes':{'inventory.analyze':['deterministic','brain'],'other_capabilities':['deterministic']},
                'query_retention':'process_lifetime','cancellation':'reserved_not_supported'}

    def query_execution(self, execution_id):
        with self._lock:
            row = self._records.get(execution_id)
            if row is None: raise RuntimeFault('EXECUTION_NOT_FOUND','NOT_FOUND','本进程没有该执行记录；历史任务请查询平台')
            return deepcopy({k:v for k,v in row.items() if k!='fingerprint'})

    def cancel_execution(self, execution_id):
        self.query_execution(execution_id)
        raise RuntimeFault('CANCELLATION_NOT_SUPPORTED','RUNTIME_ERROR','本阶段取消接口为预留，未停止或改变任何任务')

    def execute(self, value):
        try:
            request = ExecutionRequest.model_validate(value)
        except ValidationError as error:
            raw = value if isinstance(value,dict) else {}
            valid_id = lambda x: x if isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',x) else 'UNASSIGNED'
            try: target=EntityRef.model_validate(raw.get('target',{}))
            except ValidationError: target=EntityRef(entity_id='UNASSIGNED',entity_type='unknown')
            try: capability=CapabilityRef.model_validate(raw.get('capability',{}))
            except ValidationError: capability=CapabilityRef(capability_id='invalid.request',version='1.0.0')
            request = ExecutionRequest(task_id=valid_id(raw.get('task_id')),execution_id=valid_id(raw.get('execution_id')),
                capability=capability,target=target,context={})
            fault = RuntimeFault('EXECUTION_REQUEST_INVALID','VALIDATION','执行请求不符合协议',
                {'fields':[{'path':list(e['loc']),'rule':e['type']} for e in error.errors(include_input=False)]})
            return self._failure(request,ExecutionTrace(request),fault)
        digest = hashlib.sha256(json.dumps(request.model_dump(),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self._lock:
            existing = self._records.get(request.execution_id)
            if existing:
                if existing['fingerprint'] != digest:
                    fault = RuntimeFault('EXECUTION_ID_CONFLICT','VALIDATION','同一执行编号已关联不同输入')
                elif existing['result'] is not None:
                    return ExecutionResult.model_validate(deepcopy(existing['result']))
                else:
                    fault = RuntimeFault('EXECUTION_BUSY','RUNTIME_ERROR','该执行仍在运行')
                return self._failure(request,ExecutionTrace(request),fault)
            self._records[request.execution_id] = {'execution_id':request.execution_id,'task_id':request.task_id,
                                                  'status':'RUNNING','result':None,'fingerprint':digest}
        trace = ExecutionTrace(request)
        try:
            if not request.policy.read_only:
                raise RuntimeFault('WRITE_POLICY_DENIED','PERMISSION','当前 Runtime 仅开放只读能力')
            output = self.registry.invoke(request.capability,request,trace)
            result = ExecutionResult(task_id=request.task_id,execution_id=request.execution_id,target=request.target,
                                     status='COMPLETED',output=output,trace=trace.entries)
        except RuntimeFault as fault:
            result = self._failure(request,trace,fault)
        except Exception as error:
            result = self._failure(request,trace,RuntimeFault('RUNTIME_EXECUTION_FAILED','RUNTIME_ERROR','Runtime 执行失败',{'exception_type':type(error).__name__}))
        with self._lock:
            self._records[request.execution_id].update(status=result.status,result=result.model_dump())
        return result

    @staticmethod
    def _failure(request,trace,fault):
        if not trace.entries or trace.entries[-1].status != 'FAILED':
            row = trace.start(request.capability,'mf.runtime.adapter','0.1.0')
            trace.finish(row,error=fault.envelope(request,row.trace_id))
        error = fault.envelope(request,trace.entries[-1].trace_id)
        return ExecutionResult(task_id=request.task_id,execution_id=request.execution_id,target=request.target,
                               status='FAILED',trace=trace.entries,error=error)
