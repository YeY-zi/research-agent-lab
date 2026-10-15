import argparse
import json
import platform
from pathlib import Path
from .agent import demo, llm
from .tools import ToolSession


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['demo','llm'],default='demo')
    parser.add_argument('--live-search',action='store_true')
    parser.add_argument('--query',default='time series forecasting transformer')
    parser.add_argument('--model',default='gpt-4.1-mini')
    parser.add_argument('--out',default='runs/demo')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    session = ToolSession(live_search=args.live_search)
    metadata = {'mode':args.mode,'live_search':args.live_search,'query':args.query,
                'model':args.model if args.mode=='llm' else None,'python':platform.python_version()}
    try:
        if args.mode == 'demo': demo(session,args.query)
        else: llm(session,args.query,args.model)
        (out/'report.md').write_text(session.state['report'],encoding='utf-8')
        (out/'metrics.json').write_text(json.dumps(session.state['result'],indent=2),encoding='utf-8')
        metadata['status'] = 'completed'
    except Exception as exc:
        metadata['status'] = 'failed'
        metadata['error_type'] = type(exc).__name__
        raise
    finally:
        (out/'run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        (out/'trace.json').write_text(json.dumps(session.trace,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"Completed {len(session.trace)} tool calls. Report: {out/'report.md'}")
    print(json.dumps(session.state['result']['test'],indent=2))

if __name__ == '__main__': main()
