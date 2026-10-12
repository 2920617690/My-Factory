"""Fixture/Platform JSON enters the same adapter; stdout contains only JSON."""
import argparse
import json
import sys
from .bootstrap import create_runtime
from .errors import RuntimeFault
from .protocol import ErrorEnvelope,References


def main():
    parser=argparse.ArgumentParser(description='My Factory Runtime independent execution')
    parser.add_argument('command',choices=['execute','capabilities'])
    parser.add_argument('input',nargs='?',help='JSON file, or - for stdin')
    parser.add_argument('--config')
    args=parser.parse_args()
    runtime=create_runtime(args.config)
    if args.command=='capabilities':
        output=runtime.get_capabilities()
        failed=False
    else:
        try:
            text=sys.stdin.read(1_048_577) if args.input=='-' else open(args.input,encoding='utf-8').read(1_048_577)
            if len(text)>1_048_576: raise ValueError('input limit')
            result=runtime.execute(json.loads(text))
            output=result.model_dump(); failed=result.status=='FAILED'
        except (OSError,ValueError,TypeError) as error:
            output={'error':ErrorEnvelope(error_code='INVALID_JSON_INPUT',category='VALIDATION',message='输入文件或 JSON 无效',
                refs=References(task_id='UNASSIGNED',execution_id='UNASSIGNED'),details={'exception_type':type(error).__name__}).model_dump()}
            failed=True
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 1 if failed else 0
