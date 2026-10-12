"""Mock providers; business computations reuse B's unchanged JavaScript tools."""
import json
import os
from pathlib import Path
import subprocess
from typing import Annotated
from pydantic import Field, ValidationError
from .errors import RuntimeFault
from .protocol import CapabilityRef, Envelope

CURRENT = {'contract_id':'mf.mock.factory-context', 'version':'1.0.0'}


class InventoryArguments(Envelope):
    order_id: str | None = None
    order_ids: list[str] | None = None
    material_id: str | None = None
    demand: Annotated[int, Field(ge=0, le=9007199254740991)] | None = None
    target_floor: Annotated[int, Field(ge=1, le=2)] | None = None
    question: Annotated[str, Field(max_length=1600)] | None = None


class EquipmentContext(Envelope):
    entity_id: str
    floor: Annotated[int, Field(ge=1, le=2)]
    status: str
    data_mode: str


class InventoryPlugin:
    def __init__(self, registry, node, host, harness):
        self.registry, self.node, self.host, self.harness = registry, node, Path(host), harness

    def invoke(self, capability, request, trace, payload):
        if request.target.entity_type != 'warehouse':
            raise RuntimeFault('TARGET_TYPE_INVALID', 'VALIDATION', '库存分析目标应为仓库')
        try:
            contract = request.context['contract']
            original = request.context['data']
        except KeyError as error:
            raise RuntimeFault('CONTEXT_INVALID', 'VALIDATION', '缺少上下文契约或数据') from error
        # Always use the registered Data Contract provider, including internal calls.
        transformed = self.registry.invoke(CapabilityRef(capability_id='data_contract.transform', version='1.0.0'),
            request, trace, {'source_contract':contract,'target_contract':CURRENT,'payload':original})
        data = transformed['data']
        if data['warehouse_id'] != request.target.entity_id:
            raise RuntimeFault('TARGET_CONTEXT_MISMATCH', 'VALIDATION', '目标仓库与上下文不一致')
        snapshot = data['factory_state']
        try:
            args = InventoryArguments.model_validate(request.parameters).model_dump(exclude_none=True)
        except ValidationError as error:
            raise RuntimeFault('PARAMETERS_INVALID','VALIDATION','库存分析参数无效',
                {'fields':[{'path':list(e['loc']),'rule':e['type']} for e in error.errors(include_input=False)]}) from error
        args.pop('question', None)
        if not args:
            args = {'order_id':data['order_id']}
        try:
            result = subprocess.run([self.node,str(self.host)], input=json.dumps({'snapshot':snapshot,'arguments':args}),
                text=True,capture_output=True,timeout=request.policy.timeout_seconds,
                env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'TMPDIR':os.environ.get('TMPDIR','/tmp')})
            value = json.loads(result.stdout)
        except subprocess.TimeoutExpired as error:
            raise RuntimeFault('EXECUTION_TIMEOUT','RUNTIME_ERROR','工具执行超过运行时限') from error
        except Exception as error:
            raise RuntimeFault('PLUGIN_PROCESS_FAILED','PLUGIN_ERROR','库存工具进程无法运行',{'exception_type':type(error).__name__}) from error
        if result.returncode or not value['ok']:
            raise RuntimeFault('INVENTORY_INPUT_INVALID','VALIDATION','库存截面或参数未通过业务校验',{'rule':value.get('code')})
        analysis = value['value']
        if analysis['status'] != 'ok':
            raise RuntimeFault('INVENTORY_OBJECT_NOT_FOUND','NOT_FOUND','未找到指定物料或订单')
        output = {'analysis':analysis,'narrative':None,'evidence':{'execution_mode':'deterministic','numerical_source':'validated_poc_business_tool'}}
        if request.policy.mode == 'brain':
            output = self.harness.run(request,snapshot,args,analysis,trace)
        return {'data_mode':'mock','state_domain':data['state_domain'],'target':request.target.model_dump(), **output}


class EquipmentPlugin:
    def invoke(self, capability, request, trace, payload):
        if request.policy.mode != 'deterministic':
            raise RuntimeFault('MODE_NOT_SUPPORTED','VALIDATION','设备检查使用确定性执行')
        if request.target.entity_type != 'equipment' or request.parameters:
            raise RuntimeFault('EQUIPMENT_INPUT_INVALID','VALIDATION','设备目标或参数无效')
        row = request.context.get('equipment')
        if not isinstance(row,dict) or row.get('entity_id') != request.target.entity_id:
            raise RuntimeFault('EQUIPMENT_NOT_FOUND','NOT_FOUND','未找到目标设备上下文')
        try:
            EquipmentContext.model_validate(row)
        except ValidationError as error:
            raise RuntimeFault('EQUIPMENT_CONTEXT_INVALID','VALIDATION','设备模拟状态无效') from error
        if row.get('data_mode') != 'mock' or row.get('status') not in ['idle','running','maintenance','offline']:
            raise RuntimeFault('EQUIPMENT_CONTEXT_INVALID','VALIDATION','设备模拟状态无效')
        return {'entity_id':row['entity_id'],'data_mode':'mock','state_domain':'live',
                'floor':row['floor'],'status':row['status'],'requires_attention':row['status'] in ['maintenance','offline'],
                'state_effects':[]}
