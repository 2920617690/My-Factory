"""Start only the Runtime transport on loopback; other tracks own their processes."""
import sys
import json
from pathlib import Path
from urllib.request import build_opener,ProxyHandler
from urllib.error import URLError
import uvicorn

try:
    with build_opener(ProxyHandler({})).open('http://127.0.0.1:18342/api/v1/health',timeout=2) as response:
        if json.load(response).get('service')=='myfactory-runtime':
            print('My Factory Runtime 已在 http://127.0.0.1:18342 运行')
            raise SystemExit(0)
except (URLError,OSError,ValueError):
    pass
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
uvicorn.run('myfactory_runtime.service:app',host='127.0.0.1',port=18342)
