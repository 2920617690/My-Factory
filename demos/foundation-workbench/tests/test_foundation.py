"""Keyless checks for contracts, source agreement and durable gateway links."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError
from backend.adapters import AdapterError, BrainAdapter, MockSeedAdapter
from backend.contracts import BrainSubmission, FactoryState, SimulationState
from backend.store import Links
from backend.presentation import scenario_evidence

ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = MockSeedAdapter(ROOT/'fixtures/b-demo-seed.json')

    def test_original_sample_and_source_identity_survive_projection(self):
        state = self.seed.state('morning')
        row = next(r for r in state.inventory if r.material_id == 'MAT-001')
        order = next(r for r in state.orders if r.order_id == 'ORD-001')
        self.assertEqual((row.on_hand, row.reserved, row.available, order.quantity), (6,0,6,10))
        self.assertEqual(next(m for m in state.materials if m.material_id=='MAT-001').provenance.source_record_id, 'ERP-M100')
        self.assertEqual(state.data_mode, 'mock')
        self.assertEqual(state.authority, 'temporary_mock_seed')

    def test_snapshot_and_model_copy_do_not_mutate_stock(self):
        state = self.seed.state('partial_receipt')
        stock = next(r for r in state.inventory if r.material_id=='MAT-002')
        self.assertEqual((stock.on_hand,stock.quality_hold,stock.available),(270,30,140))
        stock.on_hand = 999
        self.assertEqual(next(r for r in self.seed.state('partial_receipt').inventory if r.material_id=='MAT-002').on_hand,270)

    def test_factory_contract_cannot_accept_simulation_state_or_live_mode(self):
        payload = self.seed.state('morning').model_dump(mode='json')
        for change in [{'state_domain':'simulation'},{'data_mode':'live'},{'run_id':'RUN-001'}]:
            with self.assertRaises(ValidationError):FactoryState.model_validate(payload|change)

    def test_inventory_contract_rejects_double_counting_and_floor_disagreement(self):
        payload = self.seed.state('morning').model_dump(mode='json')
        for field in ['available','floor_available']:
            bad = copy.deepcopy(payload)
            if field=='available':bad['inventory'][0]['available']=10
            else:bad['inventory'][0]['floor_available']['1']=10
            with self.assertRaises(ValidationError):FactoryState.model_validate(bad)

    def test_simulation_state_is_an_independent_logical_clock(self):
        state = SimulationState(run_id='RUN-TEST',scenario_id='C-CONTRACT-TEST',sim_time=5,inventory={'MAT-001':10})
        self.assertEqual(state.clock_unit,'minute')
        with self.assertRaises(ValidationError):SimulationState.model_validate(state.model_dump()|{'state_domain':'business_view'})

    def test_group_selection_is_canonical_and_duplicates_are_rejected(self):
        body = dict(task_id='FDN-'+'a'*32,snapshot_id='contended',question='只读核对')
        row = BrainSubmission(**body,order_ids=['ORD-1003','ORD-1001'])
        self.assertEqual(row.order_ids,['ORD-1001','ORD-1003'])
        for selection in [{},{'order_id':'ORD-1001','order_ids':['ORD-1001','ORD-1003']},{'order_ids':['ORD-1001','ORD-1001']}]:
            with self.assertRaises(ValidationError):BrainSubmission(**body,**selection)

    def test_brain_adapter_rejects_external_destinations_and_credentials(self):
        for url in ['https://api.deepseek.com','http://example.com','http://user:secret@127.0.0.1:18340','http://127.0.0.1:18340?key=private']:
            with self.assertRaises(ValueError):BrainAdapter(url)

    def b_snapshot(self):
        """Recorded mock source projected into B's actual public query fields."""
        raw = copy.deepcopy(self.seed.snapshots['contended'])
        state = self.seed.state('contended')
        raw['inventory'] = [{**r.model_dump(mode='json'),'unit':next(m.source_unit for m in state.materials if m.material_id==r.material_id),
            'floors':[{'floor':f,'available':r.floor_available[str(f)]} for f in [1,2]]} for r in state.inventory]
        return raw

    def test_all_stock_bom_purchase_and_transport_inputs_must_agree_before_model(self):
        adapter = BrainAdapter('http://127.0.0.1:18340')
        raw = self.b_snapshot()
        adapter.request = lambda *args: raw
        adapter.assert_snapshot(self.seed.state('contended'),self.seed.snapshots['contended'])
        changes=[lambda r:r['inventory'][0].update(available=7),lambda r:r['orders'][1]['bom'][0].update(per_unit=2),
            lambda r:r['inbound'][-1].update(quantity=999),lambda r:r['transport_constraints'].update(available=False)]
        for change in changes:
            raw=self.b_snapshot();change(raw);adapter.request=lambda *args:raw
            with self.assertRaises(AdapterError) as error:adapter.assert_snapshot(self.seed.state('contended'),self.seed.snapshots['contended'])
            self.assertEqual(error.exception.status,409)

    def test_task_links_are_idempotent_and_survive_a_new_process_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'links.sqlite';store=Links(path);id='FDN-'+'a'*32;body={'snapshot_id':'morning','order_id':'ORD-001','question':'只读'}
            first=store.reserve(id,body);again=store.reserve(id,body)
            self.assertEqual(first,again)
            self.assertEqual(first['upstream_id'],'MF-DEMO-'+'a'*32)
            with self.assertRaises(ValueError):store.reserve(id,body|{'question':'不同输入'})
            payload={'state':'completed','task_id':first['upstream_id'],'result':{'source':'live'}}
            store.update(id,payload=payload)
            restored=Links(path).get(id)
            self.assertEqual(json.loads(restored['payload_json']),payload)
            self.assertEqual(restored['state'],'completed')

    def test_concurrent_submissions_reserve_one_upstream_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Links(Path(directory)/'links.sqlite');id='FDN-'+'b'*32
            with ThreadPoolExecutor(max_workers=6) as pool:
                rows=list(pool.map(lambda _:store.reserve(id,{'snapshot_id':'morning'}),range(12)))
            self.assertEqual(len(store.rows()),1)
            self.assertEqual(len({r['upstream_id'] for r in rows}),1)

    def test_disconnected_B_preserves_actual_cached_record_and_marks_it_stale(self):
        from backend import server
        with tempfile.TemporaryDirectory() as directory:
            store=Links(Path(directory)/'links.sqlite');id='FDN-'+'c'*32
            link=store.reserve(id,{'snapshot_id':'morning'})
            payload={'task_id':link['upstream_id'],'state':'completed','result':{'source':'live'}}
            store.update(id,payload=payload)
            with patch.object(server,'LINKS',store), patch.object(server.BRAIN,'task',side_effect=AdapterError(503,'B 暂时未连接')):
                result=server.linked_result(id)
            self.assertEqual(result['record'],payload)
            self.assertTrue(result['cached'])
            self.assertEqual(result['upstream_error'],'B 暂时未连接')
            self.assertEqual(result['runtime_owner'],'official_B_runtime')

    def test_disconnected_B_cannot_invent_a_result_for_an_unexecuted_link(self):
        from backend import server
        with tempfile.TemporaryDirectory() as directory:
            store=Links(Path(directory)/'links.sqlite');id='FDN-'+'d'*32
            store.reserve(id,{'snapshot_id':'morning'})
            with patch.object(server,'LINKS',store), patch.object(server.BRAIN,'task',side_effect=AdapterError(503,'B 暂时未连接')):
                result=server.linked_result(id)
            self.assertIsNone(result['record'])
            self.assertFalse(result['cached'])
            self.assertEqual(result['state'],'pending')

    def test_partial_receipt_evidence_retains_released_and_held_lots(self):
        evidence=scenario_evidence(self.seed,'partial_receipt')
        self.assertEqual(evidence['previous']['snapshot_id'],'contended')
        stock=next(m for m in evidence['current']['inventory'] if m['material_id']=='MAT-002')
        receipt=[l for l in stock['lots'] if l.get('po_id')=='PO-MOCK-503']
        self.assertEqual([(l['on_hand'],l['quality']) for l in receipt],[(20,'released'),(10,'hold')])
        self.assertEqual((stock['on_hand'],stock['quality_hold'],stock['available']),(270,30,140))
        self.assertFalse(evidence['event_execution'])

    def test_original_received_comparison_is_not_a_successor_of_quality_hold(self):
        evidence=scenario_evidence(self.seed,'received')
        self.assertEqual(evidence['previous']['snapshot_id'],'morning')
        evidence['current']['lots'][0]['on_hand']=999
        self.assertEqual(self.seed.snapshots['received']['lots'][0]['on_hand'],6)

    def test_lift_constraint_changes_without_fabricating_stock_movement(self):
        evidence=scenario_evidence(self.seed,'lift_blocked')
        before=next(m for m in evidence['previous']['inventory'] if m['material_id']=='MAT-002')
        current=next(m for m in evidence['current']['inventory'] if m['material_id']=='MAT-002')
        self.assertEqual(before,current)
        self.assertTrue(evidence['previous']['transport_constraints']['available'])
        self.assertFalse(evidence['current']['transport_constraints']['available'])


if __name__=='__main__':unittest.main()
