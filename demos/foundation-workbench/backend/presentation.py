"""Read-only scenario evidence for the workbench; no event execution."""
from copy import deepcopy

PREVIOUS = {'quality_hold':'morning', 'received':'morning',
    'partial_receipt':'contended', 'quality_release':'partial_receipt',
    'group_replenished':'quality_release', 'lift_blocked':'group_replenished'}


def describe(seed, snapshot_id):
    state = seed.state(snapshot_id)
    raw = deepcopy(seed.snapshots[snapshot_id])
    raw['inventory'] = []
    for row in state.inventory:
        material = next(m for m in state.materials if m.material_id == row.material_id)
        raw['inventory'].append({'material_id':row.material_id, 'name':material.name,
            'unit':material.source_unit, 'on_hand':row.on_hand, 'reserved':row.reserved,
            'quality_hold':row.quality_hold, 'available':row.available,
            'lots':[lot for lot in raw['lots'] if lot['material_id']==row.material_id],
            'floors':[{'floor':f,'available':row.floor_available[str(f)]} for f in [1,2]],
            'inbound':[p for p in raw['inbound'] if p['material_id']==row.material_id]})
    return raw


def scenario_evidence(seed, snapshot_id):
    """Pair immutable source snapshots; original received branches from morning."""
    previous = PREVIOUS.get(snapshot_id)
    return {'current':describe(seed,snapshot_id),
        'previous':describe(seed,previous) if previous else None,
        'source':'temporary_mock_seed', 'event_execution':False}
