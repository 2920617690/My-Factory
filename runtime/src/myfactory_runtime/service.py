"""Local Platform-to-Runtime HTTP transport. No browser UI, DB or WebSocket."""
import json
import re
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .bootstrap import create_runtime
from .errors import RuntimeFault
from .protocol import ErrorEnvelope,References,ExecutionRequest,ExecutionResult

runtime=create_runtime()
app=FastAPI(title='My Factory Runtime service',version='0.1.0',docs_url='/api/docs')


def transport_error(code,category,message,execution_id='UNASSIGNED',details=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',execution_id):execution_id='UNASSIGNED'
    return {'error':ErrorEnvelope(error_code=code,category=category,message=message,
        refs=References(task_id='UNASSIGNED',execution_id=execution_id,trace_id='TRACE-'+uuid4().hex),details=details or {}).model_dump()}


@app.middleware('http')
async def platform_only(request:Request,call_next):
    if request.headers.get('host','').split(':')[0] not in ['localhost','127.0.0.1'] or request.headers.get('origin'):
        return JSONResponse(transport_error('PLATFORM_TRANSPORT_ONLY','PERMISSION','此入口仅供本机 Platform 服务调用'),status_code=403)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    return response


@app.exception_handler(RuntimeFault)
async def fault_handler(request,error):
    return JSONResponse(transport_error(error.code,error.category,error.message,request.path_params.get('execution_id','UNASSIGNED'),error.details),status_code=404 if error.category=='NOT_FOUND' else 409)


@app.get('/api/v1/health')
def health():
    return {'service':'myfactory-runtime','version':'0.1.0','task_owner':'platform','factory_state_owner':'platform',
            'data_mode':'mock','production_writes':False,'production_ready':False}


@app.get('/api/v1/capabilities')
def capabilities():
    return runtime.get_capabilities()


@app.post('/api/v1/executions')
async def execute(request:Request):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>1_048_576:
            return JSONResponse(transport_error('INPUT_TOO_LARGE','VALIDATION','输入超过 1 MiB'),status_code=413)
    try: value=json.loads(data)
    except (ValueError,UnicodeDecodeError):
        return JSONResponse(transport_error('INVALID_JSON_INPUT','VALIDATION','输入 JSON 无效'),status_code=400)
    from starlette.concurrency import run_in_threadpool
    result=await run_in_threadpool(runtime.execute,value)
    return JSONResponse(result.model_dump(),status_code=200)


@app.get('/api/v1/executions/{execution_id}')
def query(execution_id:str):
    return runtime.query_execution(execution_id)


@app.post('/api/v1/executions/{execution_id}/cancel')
def cancel(execution_id:str):
    return runtime.cancel_execution(execution_id)


def openapi_document():
    if app.openapi_schema:return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    doc=get_openapi(title=app.title,version=app.version,routes=app.routes)
    components=doc.setdefault('components',{}).setdefault('schemas',{})
    def refs(value):
        if isinstance(value,dict):
            return {k:(v.replace('#/$defs/','#/components/schemas/') if k=='$ref' else refs(v)) for k,v in value.items()}
        if isinstance(value,list):return [refs(v) for v in value]
        return value
    for model in [ExecutionRequest,ExecutionResult,ErrorEnvelope]:
        schema=model.model_json_schema()
        components.update({k:refs(v) for k,v in schema.pop('$defs',{}).items()})
        components[model.__name__]=refs(schema)
    operation=doc['paths']['/api/v1/executions']['post']
    operation['requestBody']={'required':True,'content':{'application/json':{'schema':{'$ref':'#/components/schemas/ExecutionRequest'}}}}
    operation['responses']['200']={'description':'Completed or failed execution; Platform owns Task status',
        'content':{'application/json':{'schema':{'$ref':'#/components/schemas/ExecutionResult'}}}}
    app.openapi_schema=doc
    return doc


app.openapi=openapi_document
