"""Repeatable independent checks; no model calls. Writes actual verification evidence."""
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from myfactory_runtime.bootstrap import create_runtime
from myfactory_runtime.protocol import ExecutionRequest,ExecutionResult,EntityRef,CapabilityRef,ErrorEnvelope,TraceEntry,ContractMeta,ContractRef,TaskRef,ExecutionRef,EventEnvelope


def main():
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    (evidence/'unit-tests.log').write_text(stream.getvalue())
    adapter=create_runtime()
    cases=[]
    for name in ['inventory','legacy-context','equipment']:
        request=json.loads((ROOT/f'fixtures/execution-{name}.json').read_text())
        result=adapter.execute(request)
        (evidence/f'first-{name}.json').write_text(result.model_dump_json(indent=2)+'\n')
        cases.append({'case':name,'status':result.status})
    provenance=json.loads((ROOT/'plugins/poc-inventory/provenance.json').read_text())
    source_ok=hashlib.sha256((ROOT/'plugins/poc-inventory/vendor/business.mjs').read_bytes()).hexdigest()==provenance['source_sha256']
    fixture_ok=hashlib.sha256((ROOT/'fixtures/factory-scenarios.json').read_bytes()).hexdigest()==provenance['fixture_sha256']
    schema_dir=ROOT.parent/'shared/contracts';schema_dir.mkdir(parents=True,exist_ok=True)
    models=[ExecutionRequest,ExecutionResult,EntityRef,CapabilityRef,ErrorEnvelope,TraceEntry,ContractMeta,ContractRef,TaskRef,ExecutionRef,EventEnvelope]
    for model in models:
        schema=model.model_json_schema();schema['$schema']='https://json-schema.org/draft/2020-12/schema'
        (schema_dir/(model.__name__+'.schema.json')).write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n')
    overall=tests.wasSuccessful() and all(c['status']=='COMPLETED' for c in cases) and source_ok and fixture_ok
    record={'scope':'MVP Runtime independent acceptance','checked_on':'2026-10-12','status':'PASS' if overall else 'FAIL',
        'unit_tests':{'run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors)},'fixture_runs':cases,
        'unchanged_poc_business_copy':source_ok,'unchanged_fixture_copy':fixture_ok,'public_schemas':len(models),
        'frontend_dependency':False,'platform_dependency':False,'official_model_calls_in_this_command':0,
        'task_lifecycle_owner':'platform','production_ready':False,'license_gate':'REVIEW_REQUIRED',
        'integration_gate_1':'NOT_RUN','integration_gate_2':'NOT_RUN','simulation_gate':'NOT_RUN'}
    (evidence/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(record,ensure_ascii=False,indent=2))
    return 0 if overall else 1


if __name__=='__main__':raise SystemExit(main())
