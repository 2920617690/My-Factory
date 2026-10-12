"""Platform-facing local/HTTP RuntimeClient; imports no DeepSeek implementation."""
import json
import re
from typing import Protocol
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from urllib.parse import quote


class RuntimeClient(Protocol):
    def execute(self, request:dict) -> dict: ...
    def query_execution(self, execution_id:str) -> dict: ...
    def cancel_execution(self, execution_id:str) -> dict: ...
    def get_capabilities(self) -> dict: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None


class HttpRuntimeClient:
    def __init__(self,base_url='http://127.0.0.1:18342',timeout=205):
        self.base_url,self.timeout=base_url.rstrip('/'),timeout
        self._http=build_opener(ProxyHandler({}),NoRedirect())

    def _request(self,path,value=None):
        data=None if value is None else json.dumps(value).encode()
        request=Request(self.base_url+'/api/v1/'+path,data=data,headers={'Content-Type':'application/json'})
        try:
            with self._http.open(request,timeout=self.timeout) as response:return json.load(response)
        except HTTPError as error:
            try:return json.load(error)
            except ValueError:return self._transport_error(path,value)
        except (URLError,OSError,ValueError):
            return self._transport_error(path,value)

    @staticmethod
    def _transport_error(path,value):
        raw=value if isinstance(value,dict) else {}
        valid=lambda v:v if isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',v) else 'UNASSIGNED'
        return {'error':{'error_code':'RUNTIME_TRANSPORT_UNAVAILABLE','category':'RUNTIME_ERROR',
            'message':'未取得运行结果，请查询执行记录或对账',
            'refs':{'task_id':valid(raw.get('task_id')),'execution_id':valid(raw.get('execution_id')),'entity_id':None,'trace_id':None},
            'details':{'completion_known':False}}}

    def execute(self,request):return self._request('executions',request)
    def query_execution(self,execution_id):return self._request('executions/'+quote(execution_id,safe=''))
    def cancel_execution(self,execution_id):return self._request('executions/'+quote(execution_id,safe='')+'/cancel',{})
    def get_capabilities(self):return self._request('capabilities')
