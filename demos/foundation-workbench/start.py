"""Launch the local Foundation gateway; B remains an independently owned service."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    with urllib.request.urlopen('http://127.0.0.1:18341/api/v1/health', timeout=2) as response:
        if json.load(response).get('service') == 'my-factory-foundation':
            print('Foundation 工作台已运行：http://127.0.0.1:18341/')
            sys.exit(0)
except (urllib.error.URLError, TimeoutError):
    pass
if not (ROOT/'ui/dist/index.html').is_file():
    sys.exit('请先按 app/README.md 构建页面。')
print('My Factory Foundation：http://127.0.0.1:18341/#runtime\n先启动独立 Runtime 18342；旧 B 工厂大脑页面可选接入 18340。', flush=True)
os.chdir(ROOT)
os.execve(sys.executable, [sys.executable, '-m', 'uvicorn', 'backend.server:app',
    '--host','127.0.0.1','--port','18341','--no-access-log'], dict(os.environ))
