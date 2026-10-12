import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {preferredMaterial,returnedRows,sameSelection,previousSnapshot} from '../ui/src/evidence-data.ts';

const cases=JSON.parse(readFileSync(new URL('./fixtures/scenario-tool-returns.json',import.meta.url),'utf8'));
for(const row of cases){
  const materials=returnedRows(row.inventory);
  assert.equal(materials[0].material_id,'MAT-001');
  const id=preferredMaterial(row.snapshot_id,materials.map(m=>m.material_id));
  assert.equal(id,'MAT-002');
  const stock=materials.find(m=>m.material_id===id);
  const analysis=returnedRows(row.analysis).find(m=>m.material_id===id);
  assert.deepEqual({on_hand:stock.on_hand,quality_hold:stock.quality_hold,available:stock.available,demand:analysis.demand,shortage:analysis.shortage,blocked:analysis.transfer_blocked},row.expected);
  assert.equal(stock.available,analysis.available);
  assert.equal(row.inventory.snapshot_id,row.snapshot_id);
  assert.equal(row.analysis.snapshot_id,row.snapshot_id);
  assert.equal(sameSelection({snapshot_id:row.snapshot_id,order_ids:['ORD-1001','ORD-1003']},{snapshot_id:row.snapshot_id,order_ids:['ORD-1003','ORD-1001']}),true);
  assert.equal(sameSelection({snapshot_id:row.snapshot_id,order_ids:['ORD-1001','ORD-1003']},{snapshot_id:'other_snapshot',order_ids:['ORD-1001','ORD-1003']}),false);
}
assert.equal(previousSnapshot.received,'morning');
assert.equal(sameSelection({snapshot_id:'contended',order_id:'ORD-1001'},{snapshot_id:'contended',order_ids:['ORD-1001','ORD-1003']}),false);
console.log(`PASS: ${cases.length} saved official tool returns retain changed material values; mismatched scene/order records are excluded`);
