import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from research_agent.agent import demo, llm
from research_agent.experiment import run, validate
from research_agent.tools import ToolSession, SPECS
from research_agent.local_llm import parse_calls
from research_agent.mcp_client import MCPClient


class ResearchTests(unittest.TestCase):
    def test_full_demo_measured_report(self):
        session = ToolSession()
        demo(session,'PatchTST')
        self.assertEqual([t['tool'] for t in session.trace],[s['name'] for s in SPECS])
        result = session.state['result']
        self.assertLess(result['test']['ridge_ar']['mse'],result['test']['persistence']['mse'])
        for name,metrics in result['test'].items():
            self.assertIn(f"{metrics['mse']:.6f}",session.state['report'])
        self.assertIn('bundled_method_note_not_live_search',session.state['report'])
        self.assertEqual(result,run(result['config']))

    def test_tool_order_and_invalidation(self):
        session = ToolSession()
        with self.assertRaises(KeyError): session.call('python_experiment',{})
        demo(session,'forecasting')
        session.call('configure_experiment',dict(seed=43,context=12,horizon=3,ridge=1.0))
        self.assertNotIn('result',session.state)
        session.call('paper_search',{'query':'new task'})
        self.assertEqual(set(session.state),{'papers'})

    def test_reject_untrusted_execution(self):
        session = ToolSession()
        with self.assertRaises(ValueError): session.call('shell',{'command':'echo test'})
        with self.assertRaises(ValueError): session.call('paper_search',{'query':'x','code':'print(1)'})
        for value in [True,0,1000]:
            with self.assertRaises(ValueError): validate(dict(seed=42,context=value,horizon=6,ridge=1.0))
        with self.assertRaises(ValueError): validate(dict(seed=42,context=24,horizon=6,ridge=float('nan')))

    def test_llm_tool_loop_mock_api_only(self):
        calls = [('paper_search',{'query':'forecasting'}),('method_extraction',{}),
                 ('configure_experiment',dict(seed=42,context=24,horizon=6,ridge=1.0)),
                 ('python_experiment',{}),('evaluation',{}),('experiment_summary',{})]
        class Response:
            def __init__(self,data): self.data = data
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return json.dumps(self.data).encode()
        responses = [Response({'choices':[{'message':{'content':None,'tool_calls':[
            {'id':str(i),'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}}]})
            for i,(name,args) in enumerate(calls)]
        with patch.dict('os.environ',{'OPENAI_API_KEY':'unit-test-placeholder'}),patch('urllib.request.urlopen',side_effect=responses):
            session = ToolSession()
            llm(session,'forecasting','mock-model')
        self.assertIn('report',session.state)

    def test_local_output_parser(self):
        valid = '<tool_call>{"name":"paper_search","arguments":{"query":"PatchTST"}}</tool_call>'
        self.assertEqual(parse_calls(valid)['name'],'paper_search')
        for invalid in ['hello', valid+valid, '<tool_call>{"name":"python_experiment","arguments":"shell"}</tool_call>']:
            with self.assertRaises(ValueError): parse_calls(invalid)

    def test_mcp_client_workflow_and_errors(self):
        client = MCPClient()
        try:
            with self.assertRaises(ValueError): client.call('shell',{'command':'echo test'})
            demo(client,'PatchTST')
            self.assertIn('report',client.state)
            self.assertEqual(len(client.trace),6)
            self.assertEqual(len(client.attempts),7)
            self.assertFalse(client.attempts[0]['ok'])
            self.assertTrue(all(a['ok'] for a in client.attempts[1:]))
            self.assertEqual(client.state['result']['config']['seed'],42)
        finally:
            client.close()

    def test_stdio_mcp_actual_subprocess(self):
        requests = [{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05'}},
                    {'jsonrpc':'2.0','method':'notifications/initialized'},
                    {'jsonrpc':'2.0','id':2,'method':'tools/list'}]
        for i,(name,args) in enumerate([
            ('paper_search',{'query':'forecasting'}),('method_extraction',{}),
            ('configure_experiment',dict(seed=42,context=24,horizon=6,ridge=1.0)),
            ('python_experiment',{}),('evaluation',{}),('experiment_summary',{})],3):
            requests.append({'jsonrpc':'2.0','id':i,'method':'tools/call','params':{'name':name,'arguments':args}})
        p = subprocess.run([sys.executable,'-m','research_agent.mcp'],
            input='\n'.join(json.dumps(r) for r in requests)+'\n',capture_output=True,text=True,timeout=20,check=True)
        responses = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual(len(responses),8)
        self.assertEqual(responses[0]['result']['protocolVersion'],'2024-11-05')
        self.assertEqual(len(responses[1]['result']['tools']),6)
        self.assertTrue(all(not r['result']['isError'] for r in responses[2:]))
        self.assertIn('Research Agent',responses[-1]['result']['content'][0]['text'])

if __name__ == '__main__': unittest.main()
