"""Explicit mock projection and loopback-only access to the accepted B service."""
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from .contracts import FactoryState


class AdapterError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message
        super().__init__(message)


def safe(value):
    return json.loads(re.sub(r'sk-[A-Za-z0-9_-]{12,}', '[REDACTED]', json.dumps(value, ensure_ascii=False)))


def project(snapshot: dict, digest: str) -> FactoryState:
    materials, inventory, orders = [], [], []
    for material in snapshot['materials']:
        id = material['material_id']
        lots = [lot for lot in snapshot['lots'] if lot['material_id'] == id]
        if any(lot['reserved'] < 0 or lot['on_hand'] < lot['reserved']
               or lot['quality'] not in ['released', 'hold']
               or (lot['quality'] == 'hold' and lot['reserved']) for lot in lots):
            raise ValueError('Invalid source lot')
        provenance = [{'source_system': 'mock_wms', 'source_record_id': lot['source_ref'],
            'observed_at': snapshot['as_of']} for lot in lots]
        materials.append({**material, 'unit': 'set' if material['unit'] == '套' else 'piece',
            'source_unit': material['unit'], 'provenance': {'source_system': 'mock_erp',
                'source_record_id': 'ERP-M100' if id == 'MAT-001' else f'ERP-MOCK-{id}', 'observed_at': snapshot['as_of']}})
        on_hand = sum(lot['on_hand'] for lot in lots)
        reserved = sum(lot['reserved'] for lot in lots)
        held = sum(lot['on_hand'] for lot in lots if lot['quality'] == 'hold')
        floors = {str(f): sum(lot['on_hand'] - lot['reserved'] for lot in lots
            if lot['floor'] == f and lot['quality'] == 'released') for f in [1, 2]}
        inventory.append({'material_id': id, 'on_hand': on_hand, 'reserved': reserved,
            'quality_hold': held, 'available': on_hand-reserved-held, 'version': snapshot['version'],
            'floor_available': floors, 'provenance': provenance})
    for row in snapshot['orders']:
        orders.append({key: row[key] for key in ['order_id', 'product', 'quantity', 'target_floor', 'line_id', 'due_at', 'priority', 'bom']}
            | {'provenance': {'source_system': 'mock_erp', 'source_record_id': row['source_ref'], 'observed_at': snapshot['as_of']}})
    return FactoryState(factory_name=snapshot['factory_name'], snapshot_id=snapshot['snapshot_id'],
        as_of=snapshot['as_of'], revision=snapshot['version'], seed_sha256=digest,
        materials=materials, inventory=inventory, orders=orders,
        locations=[{'location_id': row['id'], 'name': row['name'], 'floor': row['floor']} for row in snapshot['locations']])


class MockSeedAdapter:
    """Temporary immutable read source; replace through an A projection after delivery."""
    def __init__(self, path: Path):
        contents = path.read_bytes()
        self.digest = hashlib.sha256(contents).hexdigest()
        self.snapshots = {row['snapshot_id']: row for row in json.loads(contents)['scenarios']}
        self.states = {id: project(row, self.digest) for id, row in self.snapshots.items()}

    def state(self, id: str) -> FactoryState:
        if id not in self.states:
            raise AdapterError(404, '模拟截面不存在')
        return self.states[id].model_copy(deep=True)

    def scenarios(self):
        return [{key: row[key] for key in ['snapshot_id','title','description','as_of','version']}
            for row in self.snapshots.values()]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        return None


class BrainAdapter:
    def __init__(self, url: str):
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != 'http' or parsed.hostname not in ['127.0.0.1', 'localhost']
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ['', '/']):
            raise ValueError('B adapter must point at an explicit local HTTP service')
        self.url = url.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, body=None):
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        request = urllib.request.Request(self.url+path, data=payload, headers={'Content-Type':'application/json'})
        try:
            with self.opener.open(request, timeout=4) as response:
                return safe(json.load(response))
        except urllib.error.HTTPError as error:
            raise AdapterError(error.code if error.code in [400,404,409,422] else 502, 'B 服务拒绝请求，请查看运行状态') from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as error:
            raise AdapterError(503, 'B 独立服务未连接，请先启动任务 B 演示') from error

    def assert_snapshot(self, state: FactoryState, source_snapshot=None):
        raw = self.request('/api/factory/'+urllib.parse.quote(state.snapshot_id, safe=''))
        if source_snapshot is not None and any(raw.get(key) != value for key, value in source_snapshot.items()):
            raise AdapterError(409, '工作台与 B 的批次、采购或现场约束不一致，未调用模型')
        inventory = {row['material_id']: row for row in raw['inventory']}
        if raw['version'] != state.revision or raw['as_of'] != state.as_of.isoformat():
            raise AdapterError(409, '工作台与 B 数据版本不一致，未调用模型')
        for row in state.inventory:
            b = inventory.get(row.material_id, {})
            if any(b.get(key) != getattr(row, key) for key in ['on_hand','reserved','quality_hold','available']):
                raise AdapterError(409, '工作台与 B 库存截面不一致，未调用模型')
            if [b.get('floors', []), b.get('unit')] != [
                [{'floor': floor, 'available': row.floor_available[str(floor)]} for floor in [1, 2]],
                next(m.source_unit for m in state.materials if m.material_id == row.material_id)]:
                raise AdapterError(409, '工作台与 B 楼层或单位不一致，未调用模型')
        for order in state.orders:
            other = next((r for r in raw['orders'] if r['order_id'] == order.order_id), None)
            if not other or any(other[key] != value for key, value in order.model_dump(mode='json', exclude={'provenance'}).items()):
                raise AdapterError(409, '工作台与 B 订单/BOM 不一致，未调用模型')

    def task(self, id: str):
        if not re.fullmatch(r'MF-DEMO-[a-f0-9]{32}', id):
            raise AdapterError(404, 'B 任务编号不存在')
        return self.request('/api/tasks/'+id)
