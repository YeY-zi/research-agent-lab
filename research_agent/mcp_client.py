"""Small synchronous stdio client for this repository's MCP server."""
import json
import selectors
import subprocess
import sys
import time


class MCPClient:
    def __init__(self, live_search=False):
        self.live_search = live_search
        self.state, self.trace, self.attempts, self.model_trace = {}, [], [], []
        self.ident = 0
        command = [sys.executable, '-u', '-m', 'research_agent.mcp']
        if live_search: command.append('--live-search')
        self.process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,bufsize=1)
        self.protocol_trace = []
        self._request('initialize',{'protocolVersion':'2024-11-05','capabilities':{},
            'clientInfo':{'name':'research-agent-lab-client','version':'0.2.0'}})
        self._send({'jsonrpc':'2.0','method':'notifications/initialized'})
        self.specs = self._request('tools/list',{})['tools']

    def _send(self, request):
        self.protocol_trace.append({'direction':'request','message':request})
        self.process.stdin.write(json.dumps(request)+'\n')
        self.process.stdin.flush()

    def _request(self, method, params):
        self.ident += 1
        self._send({'jsonrpc':'2.0','id':self.ident,'method':method,'params':params})
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout,selectors.EVENT_READ)
            if not selector.select(timeout=45): raise TimeoutError('MCP response timeout')
        line = self.process.stdout.readline()
        if not line: raise RuntimeError('MCP server exited unexpectedly')
        response = json.loads(line)
        self.protocol_trace.append({'direction':'response','message':response})
        if response.get('id') != self.ident: raise ValueError('Mismatched MCP request id')
        if 'error' in response: raise ValueError(response['error']['message'])
        return response['result']

    def call(self,name,arguments):
        started = time.perf_counter()
        attempt = {'tool':name,'arguments':arguments}
        try:
            response = self._request('tools/call',{'name':name,'arguments':arguments})
            if response.get('isError'): raise ValueError(response['content'][0]['text'])
            value = json.loads(response['content'][0]['text'])
            if name == 'paper_search': self.state.clear()
            if name == 'configure_experiment':
                for key in ('result','evaluation','report'): self.state.pop(key,None)
            if name == 'python_experiment':
                for key in ('evaluation','report'): self.state.pop(key,None)
            key = {'paper_search':'papers','method_extraction':'methods',
                'configure_experiment':'config','python_experiment':'result',
                'evaluation':'evaluation','experiment_summary':'report'}[name]
            self.state[key] = value
            self.trace.append({'step':len(self.trace)+1,'tool':name,'arguments':arguments,'result':value})
            attempt['ok'] = True
            return value
        except Exception as exc:
            attempt.update(ok=False,error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            attempt['seconds'] = time.perf_counter()-started
            self.attempts.append(attempt)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()
