import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from myfactory_runtime.bootstrap import ROOT,create_runtime,manifest
from myfactory_runtime.data_contract import DataContracts
from myfactory_runtime.errors import RuntimeFault
from myfactory_runtime.protocol import CapabilityRef,ExecutionRequest,EventEnvelope,ContractMeta
from pydantic import ValidationError
from myfactory_runtime.registry import PluginRegistry
from myfactory_runtime.client import HttpRuntimeClient
from urllib.error import URLError


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime=create_runtime()
        self.request=json.loads((ROOT/'fixtures/execution-inventory.json').read_text())

    def run_case(self,value=None):return self.runtime.execute(value or self.request)

    def failed(self,result,code):
        self.assertEqual(result.status,'FAILED')
        self.assertEqual(result.error.error_code,code)
        self.assertTrue(result.trace)
        for e in result.trace:
            self.assertEqual((e.task_id,e.execution_id),(result.task_id,result.execution_id))
            self.assertIsNotNone(e.end)
            self.assertNotEqual(e.status,'RUNNING')

    def test_inventory_baseline(self):
        r=self.run_case();self.assertEqual(r.status,'COMPLETED')
        m=r.output['analysis']['materials'][0]
        self.assertEqual((m['available'],m['demand'],m['shortage']),(6,10,4))
        self.assertEqual(r.state_effects,[])
        self.assertEqual({t.capability.capability_id for t in r.trace},{'inventory.analyze','data_contract.transform'})

    def test_group_changes_and_blocked_transfer(self):
        rows=json.loads((ROOT/'fixtures/factory-scenarios.json').read_text())['scenarios']
        for name,expected in [('contended',60),('partial_receipt',40),('quality_release',30),('group_replenished',0),('lift_blocked',0)]:
            request=copy.deepcopy(self.request);request['execution_id']='EXEC-'+name
            request['context']['data']['factory_state']=next(r for r in rows if r['snapshot_id']==name)
            request['parameters']={'order_ids':['ORD-1001','ORD-1003']}
            result=self.run_case(request);self.assertEqual(result.status,'COMPLETED')
            mat=next(m for m in result.output['analysis']['materials'] if m['material_id']=='MAT-002')
            self.assertEqual(mat['shortage'],expected)
            self.assertEqual(mat.get('transfer_blocked'),name=='lift_blocked')

    def test_legacy_contract_input(self):
        request=json.loads((ROOT/'fixtures/execution-legacy-context.json').read_text())
        self.assertEqual(self.run_case(request).output['analysis']['materials'][0]['shortage'],4)

    def test_simulation_domain_stays_separate(self):
        self.request['context']['data']['state_domain']='simulation'
        result=self.run_case();self.assertEqual(result.output['state_domain'],'simulation');self.assertEqual(result.state_effects,[])

    def test_unknown_material(self):
        self.request['parameters']={'material_id':'MISSING','demand':10}
        self.failed(self.run_case(),'INVENTORY_OBJECT_NOT_FOUND')

    def test_unknown_order(self):
        self.request['parameters']={'order_id':'MISSING'}
        self.failed(self.run_case(),'INVENTORY_OBJECT_NOT_FOUND')

    def test_negative_and_float_demand(self):
        for number in [-1,1.5,True]:
            request=copy.deepcopy(self.request);request['execution_id']='EXEC-'+str(number)
            request['parameters']={'material_id':'MAT-001','demand':number}
            self.failed(self.run_case(request),'PARAMETERS_INVALID')

    def test_conflicting_order_arguments(self):
        self.request['parameters']={'order_id':'ORD-001','material_id':'MAT-001','demand':10}
        self.failed(self.run_case(),'INVENTORY_INPUT_INVALID')

    def test_invalid_snapshot_lot(self):
        self.request['context']['data']['factory_state']['lots'][0]['reserved']=-1
        self.failed(self.run_case(),'INVENTORY_INPUT_INVALID')

    def test_target_mismatch(self):
        self.request['target']['entity_id']='WH-OTHER'
        self.failed(self.run_case(),'TARGET_CONTEXT_MISMATCH')

    def test_unknown_capability(self):
        self.request['capability']['capability_id']='inventory.write'
        self.failed(self.run_case(),'CAPABILITY_NOT_FOUND')

    def test_unknown_capability_version(self):
        self.request['capability']['version']='9.0.0'
        self.failed(self.run_case(),'CAPABILITY_VERSION_NOT_FOUND')

    def test_write_policy_is_rejected(self):
        self.request['policy']['read_only']=False
        self.failed(self.run_case(),'WRITE_POLICY_DENIED')

    def test_invalid_request_preserves_valid_ids(self):
        self.request['policy']['timeout_seconds']=0
        result=self.run_case();self.failed(result,'EXECUTION_REQUEST_INVALID')
        self.assertEqual((result.task_id,result.execution_id),('TASK-001','EXEC-001'))

    def test_repeat_uses_same_execution_record(self):
        first=self.run_case()
        with patch('myfactory_runtime.plugins.subprocess.run',side_effect=AssertionError('must not execute twice')):
            self.assertEqual(self.run_case().model_dump(),first.model_dump())

    def test_id_conflict_keeps_original_result(self):
        first=self.run_case();changed=copy.deepcopy(self.request);changed['parameters']={'order_id':'ORD-1001'}
        self.failed(self.run_case(changed),'EXECUTION_ID_CONFLICT')
        self.assertEqual(self.runtime.query_execution('EXEC-001')['result'],first.model_dump())

    def test_plugin_timeout(self):
        with patch('myfactory_runtime.plugins.subprocess.run',side_effect=subprocess.TimeoutExpired('node',1)):
            self.failed(self.run_case(),'EXECUTION_TIMEOUT')

    def test_equipment(self):
        r=self.run_case(json.loads((ROOT/'fixtures/execution-equipment.json').read_text()))
        self.assertEqual(r.status,'COMPLETED');self.assertEqual(r.output['entity_id'],'EQ-001')

    def test_equipment_strict_floor(self):
        request=json.loads((ROOT/'fixtures/execution-equipment.json').read_text());request['context']['equipment']['floor']=True
        self.failed(self.run_case(request),'EQUIPMENT_CONTEXT_INVALID')

    def test_plugin_exception_omits_internals(self):
        def explode(*args):raise ValueError('private internal exception')
        self.runtime.registry.register(manifest('test.explode','1.0.0',['test.explode'],'test'),explode)
        self.request['capability']['capability_id']='test.explode'
        r=self.run_case();self.failed(r,'PLUGIN_INVOCATION_FAILED')
        self.assertNotIn('private internal',r.model_dump_json())

    def test_harness_missing_config_is_failure(self):
        config_path=ROOT/'config/runtime.local.json'
        if not config_path.is_file():config_path=ROOT/'config/runtime.example.json'
        config=json.loads(config_path.read_text());config['harness']['enabled']=False
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'config.json';path.write_text(json.dumps(config))
            self.runtime=create_runtime(path)
            self.request['policy']['mode']='brain'
            self.failed(self.run_case(),'HARNESS_NOT_CONFIGURED')

    def test_cancel_is_explicit_reservation(self):
        self.run_case()
        with self.assertRaises(RuntimeFault) as e:self.runtime.cancel_execution('EXEC-001')
        self.assertEqual(e.exception.code,'CANCELLATION_NOT_SUPPORTED')
        self.assertEqual(self.runtime.query_execution('EXEC-001')['status'],'COMPLETED')


class RegistryTests(unittest.TestCase):
    def test_registration_discovery_and_disposal(self):
        r=PluginRegistry();m=manifest('test.plugin','1.0.0',['test.read'],'test')
        dispose=r.register(m,lambda *args:{})
        self.assertEqual(r.discover(),[{'capability_id':'test.read','version':'1.0.0'}])
        with self.assertRaises(RuntimeFault):r.register(m,lambda *args:{})
        with self.assertRaises(RuntimeFault):r.register(manifest('other.plugin','1.0.0',['test.read'],'test'),lambda *args:{})
        self.assertEqual(len(r.manifests()),1)
        dispose();dispose();self.assertEqual(r.discover(),[])


class DataContractTests(unittest.TestCase):
    def setUp(self):
        self.dc=DataContracts()
        self.meta={'contract_id':'test.contract','version':'1.0.0','source':'test','generated_at':'2026-10-12T00:00:00Z'}
        self.schema={'type':'object','properties':{'number':{'type':'integer'}},'required':['number'],'additionalProperties':False}
        self.dc.register(self.meta,self.schema)

    def test_validation_and_version(self):
        self.assertTrue(self.dc.validate('test.contract',{'number':1},'1.0.0')['valid'])
        self.assertEqual(self.dc.resolve_version('test.contract','1.0.0')['version'],'1.0.0')
        for value in [{'number':'1'},{'number':True},{}]:
            with self.assertRaises(RuntimeFault):self.dc.validate('test.contract',value,'1.0.0')
        with self.assertRaises(RuntimeFault):self.dc.resolve_version('test.contract','9.0.0')

    def test_register_duplicate_and_invalid_schema(self):
        with self.assertRaises(RuntimeFault):self.dc.register(self.meta,self.schema)
        with self.assertRaises(RuntimeFault):self.dc.register({**self.meta,'version':'2.0.0'},{'type':'invalid'})
        for key in ['$ref','$dynamicRef','$recursiveRef']:
            with self.assertRaises(RuntimeFault):self.dc.register({**self.meta,'version':'2.0.0'},{key:'https://example.com/schema'})

    def test_successful_transform_and_invalid_result(self):
        target={**self.meta,'version':'2.0.0'};self.dc.register(target,self.schema)
        self.dc.register_transform(('test.contract','1.0.0'),('test.contract','2.0.0'),lambda p:{'number':p['number']+1})
        source={'contract_id':'test.contract','version':'1.0.0'};target={'contract_id':'test.contract','version':'2.0.0'}
        self.assertEqual(self.dc.transform(source,target,{'number':1})['data'],{'number':2})
        with self.assertRaises(RuntimeFault):self.dc.transform(target,source,{'number':1})
        self.dc._transforms[('test.contract','1.0.0','test.contract','2.0.0')]=lambda p:{'number':'bad'}
        with self.assertRaises(RuntimeFault):self.dc.transform(source,target,{'number':1})

    def test_transform_handler_failure(self):
        self.dc.register({**self.meta,'version':'2.0.0'},self.schema)
        def fail(p):raise ValueError('internal')
        self.dc.register_transform(('test.contract','1.0.0'),('test.contract','2.0.0'),fail)
        with self.assertRaises(RuntimeFault) as e:self.dc.transform({'contract_id':'test.contract','version':'1.0.0'},{'contract_id':'test.contract','version':'2.0.0'},{'number':1})
        self.assertEqual(e.exception.code,'TRANSFORM_FAILED')


class ProtocolTests(unittest.TestCase):
    def test_event_timestamp_requires_utc(self):
        event={'event_id':'EVENT-001','event_type':'plugin.completed','timestamp_utc':'2026-10-12T00:00:00Z',
               'source':'runtime','refs':{'task_id':'TASK-001','execution_id':'EXEC-001','entity_id':'WH-001'},'payload':{}}
        self.assertEqual(EventEnvelope.model_validate(event).refs.execution_id,'EXEC-001')
        for time in ['2026-10-12T08:00:00+08:00','2026-10-12T00:00:00']:
            with self.assertRaises(ValidationError):EventEnvelope.model_validate({**event,'timestamp_utc':time})

    def test_contract_metadata_requires_utc(self):
        with self.assertRaises(ValidationError):ContractMeta(contract_id='test.contract',version='1.0.0',source='test',generated_at='2026-10-12T00:00:00')

    def test_client_network_failure_has_unknown_completion(self):
        client=HttpRuntimeClient()
        with patch.object(client._http,'open',side_effect=URLError('private network information')):
            result=client.execute({'task_id':'TASK-001','execution_id':'EXEC-001'})
        self.assertFalse(result['error']['details']['completion_known'])
        self.assertEqual(result['error']['refs']['execution_id'],'EXEC-001')
        self.assertNotIn('private network',json.dumps(result))


if __name__=='__main__':unittest.main()
