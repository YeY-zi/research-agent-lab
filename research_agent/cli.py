import argparse
import json
import platform
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .agent import demo, llm
from .tools import ToolSession


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['demo','llm','local'],default='demo')
    parser.add_argument('--live-search',action='store_true')
    parser.add_argument('--query',default='time series forecasting transformer')
    parser.add_argument('--model',default=None)
    parser.add_argument('--revision')
    parser.add_argument('--model-cache')
    parser.add_argument('--transport',choices=['direct','mcp'],default='direct')
    parser.add_argument('--out',default='runs/demo')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    if args.transport == 'mcp':
        from .mcp_client import MCPClient
        session = MCPClient(live_search=args.live_search)
    else:
        session = ToolSession(live_search=args.live_search)
    metadata = {'mode':args.mode,'live_search':args.live_search,'query':args.query,
                'model':args.model or ({'local':'Qwen/Qwen3-0.6B','llm':'gpt-4.1-mini'}.get(args.mode)),'python':platform.python_version(),'transport':args.transport,
                'utc_started':datetime.now(timezone.utc).isoformat(),
                'code_revision':subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()}
    try:
        if args.mode == 'demo': demo(session,args.query)
        elif args.mode == 'llm': llm(session,args.query,args.model or 'gpt-4.1-mini')
        else:
            from .local_llm import LocalQwen, local_agent
            backend = LocalQwen(args.model or 'Qwen/Qwen3-0.6B',args.revision,args.model_cache)
            metadata['local_model'] = backend.metadata
            local_agent(session,args.query,backend)
        (out/'report.md').write_text(session.state['report'],encoding='utf-8')
        (out/'metrics.json').write_text(json.dumps(session.state['result'],indent=2),encoding='utf-8')
        metadata['status'] = 'completed'
    except Exception as exc:
        metadata['status'] = 'failed'
        metadata['error_type'] = type(exc).__name__
        raise
    finally:
        metadata['elapsed_seconds'] = time.perf_counter()-started
        metadata['utc_finished'] = datetime.now(timezone.utc).isoformat()
        metadata['successful_tool_calls'] = len(session.trace)
        metadata['attempted_tool_calls'] = len(session.attempts)
        metadata['failed_tool_calls'] = sum(not a['ok'] for a in session.attempts)
        metadata['model_rounds'] = len(session.model_trace)
        metadata['prompt_tokens'] = sum(r.get('prompt_tokens') or 0 for r in session.model_trace)
        metadata['completion_tokens'] = sum(r.get('completion_tokens') or 0 for r in session.model_trace)
        if args.transport == 'mcp':
            session.close()
            (out/'mcp-protocol.json').write_text(json.dumps(session.protocol_trace,indent=2,ensure_ascii=False),encoding='utf-8')
        (out/'tool-attempts.json').write_text(json.dumps(session.attempts,indent=2,ensure_ascii=False),encoding='utf-8')
        (out/'model-trace.json').write_text(json.dumps(session.model_trace,indent=2,ensure_ascii=False),encoding='utf-8')
        (out/'run.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        (out/'trace.json').write_text(json.dumps(session.trace,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"Completed {len(session.trace)} tool calls. Report: {out/'report.md'}")
    print(json.dumps(session.state['result']['test'],indent=2))

if __name__ == '__main__': main()
