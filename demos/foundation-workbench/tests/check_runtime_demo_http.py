"""Actual workbench -> Runtime relay checks. Never selects the model path."""
import json
from pathlib import Path
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:18341/api/v1/runtime'


def request(path, body=None, origin=None):
    headers = {'Content-Type':'application/json'}
    if origin: headers['Origin']=origin
    req=urllib.request.Request(BASE+path, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=35) as response: return response.status,json.load(response)
    except urllib.error.HTTPError as response:
        return response.code,json.load(response)


def main():
    checks=[]
    def check(name, condition):
        if not condition: raise AssertionError(name)
        checks.append({'check':name,'status':'PASS'})
    status,catalog=request('/capabilities')
    check('actual independent Runtime capability discovery',status==200 and catalog['connected'] and len(catalog['catalog']['capabilities'])==6)
    actual=[]
    def execute(demo,**extra):
        status,record=request('/demos',{'demo':demo,**extra},origin='http://127.0.0.1:18341')
        check(demo+' real relay response',status==200)
        actual.append(record)
        return record
    stock=execute('inventory')
    material=stock['result']['output']['analysis']['materials'][0]
    check('inventory baseline 6 / 10 / 4',stock['result']['status']=='COMPLETED' and
          [material[k] for k in ['available','demand','shortage']]==[6,10,4])
    expected=[('contended',60),('partial_receipt',40),('quality_release',30),('group_replenished',0),('lift_blocked',0)]
    for snapshot,shortage in expected:
        record=execute('order_group',snapshot_id=snapshot)
        material=next(m for m in record['result']['output']['analysis']['materials'] if m['material_id']=='MAT-002')
        check(snapshot+' actual shortage',record['result']['status']=='COMPLETED' and material['shortage']==shortage)
        if snapshot=='lift_blocked':
            check('enough inventory still blocked across floors',material['transfer_blocked'] is True)
    for state,attention in [('maintenance',True),('idle',False)]:
        record=execute('equipment',equipment_status=state)
        check('actual equipment '+state,record['result']['output']['requires_attention']==attention)
    legacy=execute('legacy_contract')
    check('real old-context contract transformation',legacy['result']['status']=='COMPLETED' and
        any(t['capability']['capability_id']=='data_contract.transform' and
            t['result']['contract']['version']=='1.0.0' for t in legacy['result']['trace']))
    invalid=execute('invalid_contract')
    check('unknown contract version is a retained actual failure',invalid['result']['status']=='FAILED' and
        invalid['result']['error'] is not None and any(t['status']=='FAILED' for t in invalid['result']['trace']))
    _,queried=request('/executions/'+stock['request']['execution_id'])
    check('query returns exactly the executed result',queried['result']==stock['result'])
    status,exported=request('/executions/'+stock['request']['execution_id']+'/download')
    check('HTTP download preserves the exact input and returned result',status==200 and exported==stock)
    check('all executions are read only, unique, and have no effects',all(r['request']['policy']['read_only'] and
        r['request']['policy']['mode']=='deterministic' and not r['business_state_changed'] and
        not r['result']['state_effects'] for r in actual) and
        len({r['request']['execution_id'] for r in actual})==len(actual))
    check('untrusted browser origin rejected',request('/demos',{'demo':'inventory'},origin='https://example.com')[0]==403)
    check('external destination injection rejected',request('/demos',{'demo':'inventory','url':'http://example.com'})[0]==422)
    check('non-inventory model path rejected before model call',request('/demos',{'demo':'equipment','mode':'brain'})[0]==400)
    record={'scope':'temporary workbench -> independent Runtime live relay',
        'checks':checks,'passed':len(checks),'official_model_calls':0,
        'joint_integration_gate':'NOT_RUN','runtime_results':actual}
    evidence=Path(__file__).resolve().parents[1]/'evidence/runtime-showcase-2026-10-12'
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'http-checks.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':len(checks),'official_model_calls':0,'joint_integration_gate':'NOT_RUN'},ensure_ascii=False))


if __name__=='__main__':main()
