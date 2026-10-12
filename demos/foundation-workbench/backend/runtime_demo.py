"""Temporary workbench relay to the independently running MVP Runtime.

This module owns no Factory State or production Task lifecycle. Every displayed
result comes from HttpRuntimeClient; demos only construct immutable mock inputs.
"""
from copy import deepcopy
from collections import OrderedDict
import json
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict


class RuntimeDemoSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    demo: Literal['inventory', 'order_group', 'equipment', 'legacy_contract', 'invalid_contract']
    snapshot_id: str = 'morning'
    mode: Literal['deterministic', 'brain'] = 'deterministic'
    equipment_status: Literal['idle', 'running', 'maintenance', 'offline'] = 'maintenance'


class RuntimeDemoGateway:
    def __init__(self, client, seed, fixtures: Path):
        self.client, self.seed, self.fixtures = client, seed, fixtures
        # Bounded presentation snapshots for HTTP downloads, never a TaskStore.
        self._captures, self._capture_lock = OrderedDict(), Lock()

    def capabilities(self):
        catalog = self.client.get_capabilities()
        return {'connected': isinstance(catalog.get('capabilities'), list), 'catalog': catalog,
                'gateway_role': 'temporary_runtime_delivery_demo',
                'factory_state_writes': False, 'joint_acceptance': 'NOT_RUN'}

    def build_request(self, body: RuntimeDemoSubmission):
        if body.mode == 'brain' and body.demo not in ['inventory', 'order_group']:
            raise ValueError('本演示只有库存分析支持官方大脑路径')
        fixture = ('execution-equipment.json' if body.demo == 'equipment' else
                   'execution-legacy-context.json' if body.demo == 'legacy_contract' else
                   'execution-inventory.json')
        request = json.loads((self.fixtures / fixture).read_text())
        identity = uuid4().hex
        request['task_id'] = 'FDN-MVP-DEMO-' + identity
        request['execution_id'] = 'EXEC-MVP-DEMO-' + identity
        request['policy']['mode'] = body.mode
        if body.mode == 'brain':
            request['policy']['timeout_seconds'] = 180
        if body.demo == 'equipment':
            request['context']['equipment']['status'] = body.equipment_status
        else:
            # Validate the selection with the existing immutable seed adapter.
            self.seed.state(body.snapshot_id)
            source = deepcopy(self.seed.snapshots[body.snapshot_id])
            data = request['context']['data']
            data['state' if body.demo == 'legacy_contract' else 'factory_state'] = source
            if body.demo == 'order_group':
                request['parameters'] = {'order_ids': ['ORD-1001', 'ORD-1003']}
            if body.demo == 'invalid_contract':
                request['context']['contract']['version'] = '99.0.0'
        return request

    def execute(self, body: RuntimeDemoSubmission):
        request = self.build_request(body)
        result = self.client.execute(request)
        record = {'demo': body.model_dump(), 'request': request, 'result': result,
                'gateway_role': 'temporary_runtime_delivery_demo',
                'business_state_changed': False, 'joint_acceptance': 'NOT_RUN'}
        with self._capture_lock:
            self._captures[request['execution_id']] = deepcopy(record)
            while len(self._captures) > 32:
                self._captures.popitem(last=False)
        return record

    def query(self, execution_id):
        return self.client.query_execution(execution_id)

    def captured_record(self, execution_id):
        with self._capture_lock:
            if execution_id not in self._captures:
                raise KeyError(execution_id)
            return deepcopy(self._captures[execution_id])
