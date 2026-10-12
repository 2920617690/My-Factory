"""Check the new relay's boundary and uncertainty handling without model calls."""
import copy
import json
from pathlib import Path
import unittest
from pydantic import ValidationError
from backend.adapters import AdapterError, MockSeedAdapter
from backend.runtime_demo import RuntimeDemoGateway, RuntimeDemoSubmission

ROOT = Path(__file__).resolve().parents[1]


class RuntimeDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = MockSeedAdapter(ROOT/'fixtures/b-demo-seed.json')
        cls.fixtures = next(p/'fixtures' for p in [ROOT.parent/'mvp-0.1/runtime', ROOT.parents[1]/'runtime']
                            if (p/'fixtures/execution-inventory.json').is_file())

    def gateway(self, client=None):
        return RuntimeDemoGateway(client, self.seed, self.fixtures)

    def test_groups_use_the_selected_snapshot_without_mutating_source(self):
        before = copy.deepcopy(self.seed.snapshots)
        requests = [self.gateway().build_request(RuntimeDemoSubmission(demo='order_group', snapshot_id=id))
                    for id in ['contended','partial_receipt','quality_release','group_replenished','lift_blocked']]
        self.assertEqual(len({r['execution_id'] for r in requests}),5)
        for request in requests:
            self.assertEqual(request['parameters']['order_ids'], ['ORD-1001','ORD-1003'])
            self.assertTrue(request['policy']['read_only'])
        requests[-1]['context']['data']['factory_state']['lots'][0]['on_hand'] = 999
        self.assertEqual(self.seed.snapshots, before)

    def test_transport_uncertainty_is_not_converted_to_failure_or_zero_stock(self):
        uncertain = {'error':{'error_code':'RUNTIME_TRANSPORT_UNAVAILABLE',
            'message':'未取得运行结果','details':{'completion_known':False}}}
        class Client:
            def execute(self, request): return copy.deepcopy(uncertain)
        result=self.gateway(Client()).execute(RuntimeDemoSubmission(demo='inventory'))
        self.assertEqual(result['result'],uncertain)
        self.assertNotIn('status',result['result'])
        self.assertNotIn('output',result['result'])
        self.assertFalse(result['business_state_changed'])

    def test_legacy_and_invalid_versions_reach_the_runtime_contract_provider(self):
        old=self.gateway().build_request(RuntimeDemoSubmission(demo='legacy_contract'))
        invalid=self.gateway().build_request(RuntimeDemoSubmission(demo='invalid_contract'))
        self.assertEqual(old['context']['contract']['version'],'0.1.0')
        self.assertIn('state',old['context']['data'])
        self.assertNotIn('factory_state',old['context']['data'])
        self.assertEqual(invalid['context']['contract']['version'],'99.0.0')
        self.assertEqual(json.loads((self.fixtures/'execution-inventory.json').read_text())['context']['contract']['version'],'1.0.0')

    def test_ui_cannot_supply_destinations_production_policy_or_arbitrary_commands(self):
        for extra in [{'url':'http://example.com'}, {'read_only':False}, {'command':'something'}]:
            with self.assertRaises(ValidationError):RuntimeDemoSubmission(demo='inventory',**extra)
        with self.assertRaises(ValueError):self.gateway().build_request(RuntimeDemoSubmission(demo='equipment',mode='brain'))
        with self.assertRaises(AdapterError):self.gateway().build_request(RuntimeDemoSubmission(demo='inventory',snapshot_id='missing'))


if __name__=='__main__':unittest.main()
