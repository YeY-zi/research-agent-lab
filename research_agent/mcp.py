"""Minimal newline-delimited JSON-RPC stdio MCP server (protocol 2024-11-05).

No shell/resource access. This server keeps a session for its client process.
A client requests tools in workflow order. stdout is reserved for protocol data.
"""
import json
import sys
from .tools import SPECS, ToolSession


def dispatch(request,session):
    if not isinstance(request,dict) or request.get('jsonrpc') != '2.0' or not isinstance(request.get('method'),str):
        return {'jsonrpc':'2.0','id':request.get('id') if isinstance(request,dict) else None,
                'error':{'code':-32600,'message':'Invalid Request'}}
    if 'id' not in request: return None
    ident = request['id']
    method = request['method']
    params = request.get('params',{})
    if not isinstance(params,dict):
        return {'jsonrpc':'2.0','id':ident,'error':{'code':-32602,'message':'Invalid params'}}
    if method == 'initialize':
        result = {'protocolVersion':'2024-11-05','capabilities':{'tools':{'listChanged':False}},
                  'serverInfo':{'name':'research-agent-lab','version':'0.1.0'}}
    elif method == 'ping': result = {}
    elif method == 'tools/list': result = {'tools':SPECS}
    elif method == 'tools/call':
        try:
            value = session.call(params.get('name'),params.get('arguments',{}))
            result = {'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False)}],'isError':False}
        except Exception as exc:
            result = {'content':[{'type':'text','text':f'{type(exc).__name__}: {exc}'}],'isError':True}
    else:
        return {'jsonrpc':'2.0','id':ident,'error':{'code':-32601,'message':'Method not found'}}
    return {'jsonrpc':'2.0','id':ident,'result':result}


def main():
    session = ToolSession(live_search='--live-search' in sys.argv)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = dispatch(request,session)
        except json.JSONDecodeError:
            response = {'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if response is not None:
            print(json.dumps(response,ensure_ascii=False),flush=True)

if __name__ == '__main__': main()
