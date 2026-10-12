/** Read-only batch-level checks for synthetic, separately versioned snapshots. */
import { readFileSync } from 'node:fs';

export function loadSnapshot(path, id) {
  const root = JSON.parse(readFileSync(path, 'utf8'));
  const snapshot = root.scenarios.find(row => row.snapshot_id === id);
  if (!snapshot || snapshot.data_mode !== 'mock' || snapshot.factory_id !== 'FACTORY-001') throw new Error('INVALID_SNAPSHOT');
  const materials = new Set(snapshot.materials.map(row => row.material_id));
  const locations = new Map(snapshot.locations.map(row => [row.id, row]));
  const lotIds = new Set();
  for (const lot of snapshot.lots) {
    if (!materials.has(lot.material_id) || !locations.has(lot.location_id) || lotIds.has(lot.lot_id)
        || locations.get(lot.location_id).floor !== lot.floor || !['released', 'hold'].includes(lot.quality)
        || !Number.isSafeInteger(lot.on_hand) || !Number.isSafeInteger(lot.reserved)
        || lot.on_hand < 0 || lot.reserved < 0 || lot.reserved > lot.on_hand
        || (lot.quality === 'hold' && lot.reserved !== 0)) throw new Error('INVALID_LOT');
    lotIds.add(lot.lot_id);
  }
  for (const order of snapshot.orders) {
    if (!Number.isSafeInteger(order.quantity) || order.quantity < 0 || ![1, 2].includes(order.target_floor)
        || new Set(order.bom.map(row => row.material_id)).size !== order.bom.length
        || order.bom.some(row => !materials.has(row.material_id) || !Number.isSafeInteger(row.per_unit) || row.per_unit <= 0)) {
      throw new Error('INVALID_ORDER');
    }
  }
  if (new Set(snapshot.orders.map(row => row.order_id)).size !== snapshot.orders.length) throw new Error('DUPLICATE_ORDER');
  for (const po of snapshot.inbound.filter(row => row.ordered_quantity !== undefined)) {
    const quantities = [po.quantity, po.ordered_quantity, po.received_quantity];
    const received = snapshot.lots.filter(row => row.po_id === po.po_id);
    if (quantities.some(q => !Number.isSafeInteger(q) || q < 0)
      || po.quantity + po.received_quantity !== po.ordered_quantity
      || received.some(row => row.material_id !== po.material_id)
      || received.reduce((sum, row) => sum + row.on_hand, 0) !== po.received_quantity
      || po.confirmed_receipt !== (po.quantity === 0)) throw new Error('INVALID_PARTIAL_RECEIPT');
  }
  if (snapshot.transport_constraints && (snapshot.transport_constraints.from_floor !== 1
    || snapshot.transport_constraints.to_floor !== 2 || typeof snapshot.transport_constraints.available !== 'boolean')) throw new Error('INVALID_TRANSPORT_CONSTRAINT');
  return snapshot;
}

export function inventory(snapshot, materialId) {
  if (typeof materialId !== 'string' || !materialId) throw new Error('INVALID_MATERIAL');
  if (materialId === '*') return { status: 'ok', ...metadata(snapshot), materials: snapshot.materials.map(m => inventory(snapshot, m.material_id)) };
  const material = snapshot.materials.find(row => row.material_id === materialId);
  if (!material) return { status: 'not_found', material_id: materialId, ...metadata(snapshot) };
  const lots = snapshot.lots.filter(row => row.material_id === materialId);
  const sum = (rows, field) => rows.reduce((total, row) => total + row[field], 0);
  const on_hand = sum(lots, 'on_hand');
  const reserved = sum(lots, 'reserved');
  const held = sum(lots.filter(row => row.quality === 'hold'), 'on_hand');
  const floors = [1, 2].map(floor => {
    const rows = lots.filter(row => row.floor === floor);
    return { floor, available: sum(rows.filter(row => row.quality === 'released'), 'on_hand') - sum(rows, 'reserved') };
  });
  return { status: 'ok', ...material, on_hand, reserved, quality_hold: held, available: on_hand - reserved - held,
    floors, lots, inbound: snapshot.inbound.filter(row => row.material_id === materialId), ...metadata(snapshot) };
}

function metadata(snapshot) {
  return { factory_id: snapshot.factory_id, data_mode: 'mock', source_system: snapshot.source_system,
    snapshot_id: snapshot.snapshot_id, as_of: snapshot.as_of, version: snapshot.version,
    ...(snapshot.business_events ? { business_events: snapshot.business_events, transport_constraints: snapshot.transport_constraints } : {}) };
}

export function shortage(snapshot, materialId, demand, targetFloor = 2) {
  if (!Number.isSafeInteger(demand) || demand < 0 || ![1, 2].includes(targetFloor)) throw new Error('INVALID_DEMAND_OR_FLOOR');
  const stock = inventory(snapshot, materialId);
  if (materialId === '*') throw new Error('MATERIAL_ID_REQUIRED_FOR_SINGLE_DEMAND');
  if (stock.status !== 'ok') return stock;
  const local = stock.floors.find(row => row.floor === targetFloor).available;
  const shortage = Math.max(0, demand - stock.available);
  const line_shortage = Math.max(0, demand - local);
  const transfer_quantity = Math.min(line_shortage, stock.available - local);
  const blocked = targetFloor === 2 && snapshot.transport_constraints?.available === false;
  return { material_id: materialId, name: stock.name, unit: stock.unit, on_hand: stock.on_hand,
    reserved: stock.reserved, quality_hold: stock.quality_hold, available: stock.available, demand,
    shortage, feasible: shortage === 0, target_floor: targetFloor, local_available: local,
    line_shortage, transfer_quantity, line_ready: line_shortage === 0,
    ...(snapshot.transport_constraints ? { transfer_blocked: blocked && transfer_quantity > 0,
      transfer_status: transfer_quantity === 0 ? 'not_needed' : blocked ? 'blocked' : 'requires_preparation' } : {}),
    inbound_excluded: stock.inbound.filter(row => !row.confirmed_receipt),
    reasons: [
      ...(stock.reserved ? [`${stock.reserved}${stock.unit}已被其他需求预留`] : []),
      ...(stock.quality_hold ? [`${stock.quality_hold}${stock.unit}待检，不计可用量`] : []),
      ...(transfer_quantity ? [blocked ? `需跨层备料${transfer_quantity}${stock.unit}，但提升通道停用` : `可从另一楼层备料${transfer_quantity}${stock.unit}，未下发搬运指令`] : []),
      ...(shortage ? [`全厂可用量不足${shortage}${stock.unit}`] : []),
    ], ...metadata(snapshot) };
}

export function analyze(snapshot, args) {
  if (args.order_ids !== undefined) return analyzeGroup(snapshot, args);
  if (args.order_id) {
    if (args.material_id !== undefined || args.demand !== undefined || args.target_floor !== undefined) throw new Error('ORDER_AND_MATERIAL_ARGUMENTS_CONFLICT');
    const order = snapshot.orders.find(row => row.order_id === args.order_id);
    if (!order) return { status: 'not_found', order_id: args.order_id, ...metadata(snapshot) };
    const materials = order.bom.map(row => shortage(snapshot, row.material_id, row.per_unit * order.quantity, order.target_floor));
    return { status: 'ok', order, materials, feasible: materials.every(row => row.feasible),
      line_ready: materials.every(row => row.line_ready), shortages: materials.filter(row => row.shortage > 0),
      transfers: materials.filter(row => row.transfer_quantity > 0),
      allocation_mode: 'independent_order_check_no_stock_consumption', ...metadata(snapshot) };
  }
  if (typeof args.material_id !== 'string' || args.demand === undefined) throw new Error('MATERIAL_AND_DEMAND_OR_ORDER_REQUIRED');
  return { status: 'ok', ...shortage(snapshot, args.material_id, args.demand, args.target_floor ?? 2) };
}

/** Shared BOM demand is compared once with stock; no priority optimization or allocation. */
function analyzeGroup(snapshot, args) {
  if (['order_id', 'material_id', 'demand', 'target_floor'].some(key => args[key] !== undefined)) throw new Error('GROUP_ARGUMENTS_CONFLICT');
  const ids = args.order_ids;
  if (!Array.isArray(ids) || ids.length < 2 || ids.length > 5 || ids.some(id => typeof id !== 'string')
    || new Set(ids).size !== ids.length) throw new Error('INVALID_ORDER_GROUP');
  const orders = [...ids].sort().map(id => snapshot.orders.find(row => row.order_id === id));
  if (orders.some(row => !row)) return { status: 'not_found', order_ids: [...ids].sort(), ...metadata(snapshot) };
  if (new Set(orders.map(row => row.target_floor)).size !== 1) throw new Error('MIXED_TARGET_FLOORS_UNSUPPORTED');
  const demands = new Map();
  for (const order of orders) for (const row of order.bom) {
    const demand = order.quantity * row.per_unit;
    const entry = demands.get(row.material_id) ?? { total: 0, contributors: [] };
    entry.total += demand;
    if (!Number.isSafeInteger(entry.total)) throw new Error('INVALID_GROUP_DEMAND');
    entry.contributors.push({ order_id: order.order_id, demand });
    demands.set(row.material_id, entry);
  }
  const materials = [...demands.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([id, entry]) => ({
    ...shortage(snapshot, id, entry.total, orders[0].target_floor), contributors: entry.contributors,
  }));
  const independent_checks = orders.map(order => {
    const result = analyze(snapshot, { order_id: order.order_id });
    return { order_id: order.order_id, feasible: result.feasible, line_ready: result.line_ready };
  });
  return { status: 'ok', order_ids: orders.map(row => row.order_id), orders, independent_checks, materials,
    feasible: materials.every(row => row.feasible), line_ready: materials.every(row => row.line_ready),
    shortages: materials.filter(row => row.shortage > 0), transfers: materials.filter(row => row.transfer_quantity > 0),
    conflicts: materials.filter(row => row.contributors.length > 1 && row.shortage > 0),
    allocation_mode: 'shared_demand_check_no_allocation_or_stock_consumption', ...metadata(snapshot) };
}
