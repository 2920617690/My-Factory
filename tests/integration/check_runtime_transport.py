"""Runtime handoff checks only; this does not claim Frontend/Platform integration."""
import json
from pathlib import Path
import sys
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'runtime/src'))
from myfactory_runtime.client import HttpRuntimeClient
from myfactory_runtime.protocol import ExecutionResult


def main():
    client=HttpRuntimeClient();checks=[]
    request=json.loads((ROOT/'runtime/fixtures/execution-inventory.json').read_text())
    request['execution_id']='EXEC-HTTP-001'
    assert any(c['capability_id']=='inventory.analyze' for c in client.get_capabilities()['capabilities']);checks.append('capability_discovery')
    result=client.execute(request);assert result['status']=='COMPLETED';checks.append('standard_execution')
    row=result['output']['analysis']['materials'][0];assert (row['available'],row['demand'],row['shortage'])==(6,10,4);checks.append('baseline_6_10_4')
    Draft202012Validator(ExecutionResult.model_json_schema()).validate(result);checks.append('result_json_schema')
    assert client.query_execution('EXEC-HTTP-001')['result']==result;checks.append('query_execution')
    assert client.execute(request)==result;checks.append('idempotent_same_process')
    changed={**request,'parameters':{'order_id':'ORD-1001'}}
    assert client.execute(changed)['error']['error_code']=='EXECUTION_ID_CONFLICT';checks.append('id_conflict')
    unknown={**request,'execution_id':'EXEC-HTTP-MISSING','capability':{'capability_id':'unknown.capability','version':'1.0.0'}}
    failed=client.execute(unknown);assert failed['status']=='FAILED' and failed['trace'][0]['end'];checks.append('structured_failure_trace')
    assert client.cancel_execution('EXEC-HTTP-001')['error']['error_code']=='CANCELLATION_NOT_SUPPORTED';checks.append('honest_cancel_reservation')
    http=build_opener(ProxyHandler({}))
    for headers,body,status,code in [({'Origin':'http://127.0.0.1:18341'},json.dumps(request).encode(),403,'PLATFORM_TRANSPORT_ONLY'),({},b'broken json',400,'INVALID_JSON_INPUT')]:
        try:http.open(Request('http://127.0.0.1:18342/api/v1/executions',data=body,headers=headers))
        except HTTPError as error:
            value=json.load(error);assert error.code==status and value['error']['error_code']==code and value['error']['refs']
        else:raise AssertionError('rejection required')
        checks.append(code.lower())
    with http.open('http://127.0.0.1:18342/openapi.json') as response:
        document=json.load(response)
        assert document['paths']['/api/v1/executions']['post']['requestBody']['content']['application/json']['schema']['$ref'].endswith('ExecutionRequest')
    checks.append('openapi_execution_contract')
    output={'scope':'runtime_transport_only','status':'PASS','checks':checks,'result':result,'joint_integration':'NOT_RUN'}
    (ROOT/'runtime/evidence/http-handoff-checks.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print({'status':'PASS','checks':len(checks),'scope':'runtime_transport_only'})


if __name__=='__main__':main()
