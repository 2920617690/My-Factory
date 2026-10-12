"""Local integration entry point; no production credentials or inventory write route."""
import json
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .adapters import AdapterError, BrainAdapter, MockSeedAdapter
from .contracts import BrainSubmission, FactoryState, SimulationRequest, SimulationState
from .store import Links, now
from .presentation import scenario_evidence
from .runtime_demo import RuntimeDemoGateway, RuntimeDemoSubmission

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = ROOT.parent
RUNTIME_ROOT = Path(os.environ['MYFACTORY_RUNTIME_DIR']) if os.environ.get('MYFACTORY_RUNTIME_DIR') else next(
    (p for p in [FOUNDATION/'mvp-0.1/runtime', ROOT.parents[1]/'runtime']
     if (p/'src/myfactory_runtime/client.py').is_file()), FOUNDATION/'mvp-0.1/runtime')
sys.path.insert(0, str(RUNTIME_ROOT/'src'))
from myfactory_runtime.client import HttpRuntimeClient
CONFIG = json.loads((ROOT/'config/adapters.json').read_text())
if CONFIG['production_writes'] or CONFIG['factory_state']['mode'] != 'mock_seed':
    raise RuntimeError('This milestone only supports the explicit read-only mock seed adapter')
SEED = MockSeedAdapter(ROOT/'fixtures/b-demo-seed.json')
BRAIN = BrainAdapter(CONFIG['brain']['url'])
LINKS = Links(ROOT/'state/links.sqlite')
RUNTIME_DEMO = RuntimeDemoGateway(HttpRuntimeClient('http://127.0.0.1:18342'), SEED, RUNTIME_ROOT/'fixtures')
app = FastAPI(title='SVS My Factory Foundation', version='0.1.0', docs_url='/api/docs', redoc_url=None)


@app.exception_handler(AdapterError)
async def adapter_error(_request, error):
    return JSONResponse({'detail': error.message}, status_code=error.status)


@app.middleware('http')
async def local_only(request: Request, call_next):
    if request.headers.get('host', '').split(':')[0] not in ['127.0.0.1', 'localhost']:
        return JSONResponse({'detail': '当前开发入口只接受本机访问'}, status_code=403)
    if request.method not in ['GET', 'HEAD'] and request.headers.get('origin') not in [
        None, 'http://127.0.0.1:18341', 'http://localhost:18341']:
        return JSONResponse({'detail': '请求来源被拒绝'}, status_code=403)
    result = await call_next(request)
    result.headers['Cache-Control'] = 'no-store'
    result.headers['X-Content-Type-Options'] = 'nosniff'
    result.headers['Referrer-Policy'] = 'no-referrer'
    return result


def workflow():
    path = FOUNDATION/'status/workflow.json'
    if not path.is_file():
        path = ROOT/'fixtures/workflow-status.json'
    return json.loads(path.read_text())


@app.get('/api/v1/runtime/capabilities')
def runtime_capabilities():
    return RUNTIME_DEMO.capabilities()


@app.post('/api/v1/runtime/demos')
def runtime_demo(body: RuntimeDemoSubmission):
    try:
        return RUNTIME_DEMO.execute(body)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get('/api/v1/runtime/executions/{execution_id}')
def runtime_execution(execution_id: str):
    return RUNTIME_DEMO.query(execution_id)


@app.get('/api/v1/runtime/executions/{execution_id}/download')
def runtime_download(execution_id: str):
    try:
        record = RUNTIME_DEMO.captured_record(execution_id)
    except KeyError:
        raise HTTPException(404, '本工作台进程未保留该演示记录，请重新执行并及时导出')
    return JSONResponse(record, headers={'Content-Disposition':f'attachment; filename="{record["request"]["execution_id"]}.json"'})


@app.get('/api/v1/health')
def health():
    brain, error = None, None
    try:
        brain = BRAIN.request('/api/health')
        if brain.get('provider') != 'DeepSeek 官方 API' or brain.get('sdk_version') != '0.1.5rc1':
            brain, error = None, 'B 服务未返回锁定的官方验证环境信息'
    except AdapterError as exc:
        error = exc.message
    tasks = workflow()['tasks']
    return {'service': 'my-factory-foundation', 'version': '0.1.0', 'observed_at': now(),
        'milestone': 'M1_INTEGRATION_STARTER', 'data_mode': 'mock', 'production_ready': False,
        'license_gate': 'REVIEW_REQUIRED', 'brain': {'connected': brain is not None, 'health': brain, 'error': error},
        'modules': [{'id': t['id'], 'validation_status': t['status'], 'owner': t['owner'],
            'connection': 'connected' if t['id']=='MF-P0-B' and brain else 'awaiting_delivery'} for t in tasks],
        'integration_acceptance': workflow()['integration']['status'],
        'factory_state_source': 'temporary_mock_seed', 'production_writes': False}


@app.get('/api/v1/scenarios')
def scenarios():
    return {'scenarios': SEED.scenarios(), 'data_mode': 'mock', 'source': 'temporary_mock_seed'}


@app.get('/api/v1/scenario-evidence')
def evidence(snapshot_id: str = 'contended'):
    return scenario_evidence(SEED, snapshot_id)


@app.get('/api/v1/factory-state', response_model=FactoryState)
def factory_state(snapshot_id: str = 'morning'):
    return SEED.state(snapshot_id)


@app.get('/api/v1/inventory/{material_id}')
def material_inventory(material_id: str, snapshot_id: str = 'morning'):
    state = SEED.state(snapshot_id)
    row = next((r for r in state.inventory if r.material_id == material_id), None)
    if row is None:
        raise HTTPException(404, '物料不存在')
    return {'state_domain': state.state_domain, 'data_mode': state.data_mode, 'snapshot_id': snapshot_id,
        'inventory': row.model_dump(mode='json')}


@app.get('/api/v1/contracts')
def contracts():
    return {'factory_state': FactoryState.model_json_schema(), 'simulation_state': SimulationState.model_json_schema(),
        'simulation_request': SimulationRequest.model_json_schema(), 'brain_submission': BrainSubmission.model_json_schema(),
        'policy': {'inventory_write': False, 'simulation_writeback': False, 'agv_dispatch': False,
            'professional_algorithms': 'later_tools', 'factory_state_adapter': 'mock_seed_until_A_delivery',
            'c_adapter': 'reserved_until_C_delivery', 'simulation_clock_unit': 'minute'}}


@app.get('/api/v1/tools')
def tools():
    return {'registered_in_B': [
        {'name':'factory_inventory_query','permission':'read_mock','owner':'B','description':'查询批次、预留、质量与楼层库存'},
        {'name':'factory_shortage_analyze','permission':'read_mock','owner':'B','description':'单订单或订单组共同需求核对'}],
        'reserved_not_registered': [
            {'name':'factory.simulation.run','owner':'C','status':'AWAITING_DELIVERY'},
            {'name':'factory.scheduling.optimize','owner':'future_algorithm_tool','status':'PLANNED'},
            {'name':'factory.inventory.optimize','owner':'future_algorithm_tool','status':'PLANNED'},
            {'name':'factory.agv.plan','owner':'future_algorithm_tool','status':'PLANNED'}]}


def linked_result(id):
    try:
        link = LINKS.get(id)
    except KeyError:
        raise HTTPException(404, '工作台任务不存在')
    cached = False
    upstream_error = None
    try:
        record = BRAIN.task(link['upstream_id'])
        LINKS.update(id, payload=record)
    except AdapterError as exc:
        record = json.loads(link['payload_json']) if link['payload_json'] else None
        cached = record is not None
        upstream_error = exc.message
    return {'task_id': id, 'upstream_task_id': link['upstream_id'], 'created_at': link['created_at'],
        'input': json.loads(link['input_json']), 'state': record['state'] if record else 'pending',
        'record': record, 'cached': cached, 'upstream_error': upstream_error,
        'observed_at': now(), 'runtime_owner':'official_B_runtime', 'state_domain':'business_view'}


@app.post('/api/v1/brain/tasks')
def submit(body: BrainSubmission):
    state = SEED.state(body.snapshot_id)
    ids = body.order_ids if body.order_ids is not None else [body.order_id]
    if any(id not in {o.order_id for o in state.orders} for id in ids):
        raise HTTPException(400, '所选订单不存在')
    input = body.model_dump(exclude={'task_id'}, exclude_none=True)
    try:
        existing = LINKS.get(body.task_id)
        if json.loads(existing['input_json']) != input:
            raise HTTPException(409, '工作台任务编号已用于其他输入')
        if existing['payload_json']:
            return linked_result(body.task_id)
    except KeyError:
        pass
    BRAIN.assert_snapshot(state, SEED.snapshots[state.snapshot_id])
    try:
        link = LINKS.reserve(body.task_id, input)
    except ValueError:
        raise HTTPException(409, '工作台任务编号已用于其他输入')
    try:
        BRAIN.request('/api/tasks', {'task_id':link['upstream_id'], **input})
    except AdapterError as exc:
        LINKS.update(body.task_id, error=exc.message)
        raise
    return linked_result(body.task_id)


@app.get('/api/v1/brain/tasks/{task_id}')
def task(task_id: str):
    return linked_result(task_id)


@app.get('/api/v1/brain/tasks/{task_id}/download')
def download(task_id: str):
    return JSONResponse(linked_result(task_id), headers={'Content-Disposition': f'attachment; filename="{task_id}.json"'})


@app.get('/api/v1/brain/history')
def history():
    return BRAIN.request('/api/tasks') | {'runtime_owner':'official_B_runtime'}


@app.get('/api/v1/brain/runs/{upstream_task_id}')
def upstream_run(upstream_task_id: str):
    return {'record': BRAIN.task(upstream_task_id), 'runtime_owner':'official_B_runtime', 'observed_at': now()}


@app.get('/api/v1/runtime/links')
def links():
    return {'links': [{'task_id': r['task_id'], 'upstream_task_id':r['upstream_id'], 'state':r['state'],
        'created_at':r['created_at'], 'updated_at':r['updated_at'], 'error':r['error']} for r in LINKS.rows()],
        'storage_role':'gateway_task_links_only', 'business_inventory_storage':False}


@app.get('/api/v1/simulation/scenarios')
def simulation_scenarios():
    return {'connection':'awaiting_delivery', 'scenarios':[], 'owner':'C',
        'acceptance_targets': {'clock_unit':'minute','baseline_final_inventory':3,'replenish_final_inventory':7},
        'targets_are_results':False, 'writeback_to_business_state':False}


@app.post('/api/v1/simulation/runs')
def simulation_run(_body: SimulationRequest):
    raise HTTPException(503, '任务 C 尚未交付；仿真接口已预留，未生成或冒充 SimPy 运行结果')


@app.post('/api/v1/mock-events')
def mock_event(_body: dict):
    raise HTTPException(403, '工作台不开放库存写入；A 的模拟写事件仍由 A 鉴权、幂等与版本校验')


app.mount('/assets', StaticFiles(directory=ROOT/'ui/dist/assets'), name='assets')


@app.get('/')
def index():
    return FileResponse(ROOT/'ui/dist/index.html')
