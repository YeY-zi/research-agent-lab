import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from .experiment import run, validate

PAPERS = [
    {'id':'2211.14730','title':'A Time Series is Worth 64 Words: Long-term Forecasting with Transformers',
     'url':'https://arxiv.org/abs/2211.14730',
     'text':'This bundled human-written method note describes PatchTST: partition time series into patches and use channel-independent Transformer modeling. It is not a fetched abstract.',
     'source':'bundled_method_note_not_live_search'},
    {'id':'2403.07815','title':'Chronos: Learning the Language of Time Series',
     'url':'https://arxiv.org/abs/2403.07815',
     'text':'This bundled human-written method note describes Chronos: scale and quantize time series into tokens, then train language models for probabilistic forecasting. It is not a fetched abstract.',
     'source':'bundled_method_note_not_live_search'}]


def search_papers(query, live=False):
    if not live:
        terms = set(re.findall(r'[a-z0-9]+',query.lower()))
        return sorted(PAPERS,key=lambda p: -len(terms & set(re.findall(r'[a-z0-9]+',(p['title']+' '+p['text']).lower()))))
    url = 'https://export.arxiv.org/api/query?'+urllib.parse.urlencode({'search_query':'all:'+query,'max_results':3})
    request = urllib.request.Request(url,headers={'User-Agent':'ResearchAgentLab/0.1'})
    with urllib.request.urlopen(request,timeout=30) as response:
        root = ET.fromstring(response.read(2_000_000))
    ns = {'a':'http://www.w3.org/2005/Atom'}
    papers = []
    for entry in root.findall('a:entry',ns):
        link = entry.findtext('a:id','',ns)
        if not link.startswith(('http://arxiv.org/abs/','https://arxiv.org/abs/')):
            raise ValueError('Unexpected arXiv entry URL')
        papers.append({'id':link.rsplit('/',1)[-1], 'title':' '.join(entry.findtext('a:title','',ns).split()),
            'url':link,'text':' '.join(entry.findtext('a:summary','',ns).split()),'source':'live_arxiv_abstract'})
    return papers


def extract_methods(papers):
    # Extract evidence instead of inventing implementation/hyperparameters.
    return [{'paper_id':p['id'],'title':p['title'],'url':p['url'],'source':p['source'],
             'method_evidence':p['text'], 'extraction':'verbatim abstract/note; no full-text reasoning',
             'missing':['training recipe','verified hyperparameters','official code commit']} for p in papers]


def evaluate_result(result):
    baseline = result['test']['persistence']['mse']
    candidate = result['test']['ridge_ar']['mse']
    return {'mse_reduction_vs_persistence':(baseline-candidate)/baseline if baseline else None,
            'selected_on_validation':result['selected_on_validation'],
            'scope':'Only this synthetic dataset and seed; unrelated to cited paper performance.'}


def summary(methods, result, evaluation):
    lines = ['# Research Agent 实验报告','',
        '本次运行真实执行了 Python 合成数据实验；论文笔记用于研究背景，未复现所引用论文模型。','',
        '## 文献来源','']
    for m in methods:
        lines += [f"- [{m['title']}]({m['url']}) — `{m['source']}`",f"  - 方法证据：{m['method_evidence']}"]
    lines += ['', '## 实验配置','', '```json',json.dumps(result['config'],indent=2),'```','',
        f"数据：`{result['dataset']}`；先切分时间轴，再构造窗口；仅用训练段拟合归一化。",
        f"窗口数量：{result['windows']}。",'',
        '| 模型 | Validation MSE | Test MSE | Test MAE |','|---|---:|---:|---:|']
    for model in result['test']:
        lines.append(f"| {model} | {result['validation'][model]['mse']:.6f} | {result['test'][model]['mse']:.6f} | {result['test'][model]['mae']:.6f} |")
    reduction = evaluation['mse_reduction_vs_persistence']
    lines += ['',f"验证集选出的模型：`{result['selected_on_validation']}`。",
              f"Ridge AR 相对 persistence 的测试 MSE 降幅：{reduction:.2%}。" if reduction is not None else 'Baseline MSE 为零，降幅未定义。',
              '', '## 局限','']+[f'- {v}' for v in result['limitations']]
    return '\n'.join(lines)+'\n'


def spec(name, description, properties, required):
    return {'name':name,'description':description,'inputSchema':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}

SPECS = [
    spec('paper_search','Search arXiv or explicitly labeled offline method notes.',{'query':{'type':'string'}},['query']),
    spec('method_extraction','Extract cited evidence from previously searched papers.',{},[]),
    spec('configure_experiment','Configure a fixed synthetic ridge-AR baseline experiment. Does not reproduce papers.',
         {'seed':{'type':'integer'},'context':{'type':'integer'},'horizon':{'type':'integer'},'ridge':{'type':'number'}},['seed','context','horizon','ridge']),
    spec('python_experiment','Run the configured allowlisted Python experiment.',{},[]),
    spec('evaluation','Compute comparisons from actual measured results.',{},[]),
    spec('experiment_summary','Render a report using actual citations and measured metrics.',{},[])]


class ToolSession:
    def __init__(self,live_search=False):
        self.live_search = live_search
        self.state = {}
        self.trace = []

    def call(self,name,arguments):
        specifications = {s['name']:s for s in SPECS}
        if name not in specifications: raise ValueError('Unknown tool')
        schema = specifications[name]['inputSchema']
        if not isinstance(arguments,dict) or set(arguments)-set(schema['properties']) or set(schema['required'])-set(arguments):
            raise ValueError('Unexpected or missing tool arguments')
        if name == 'paper_search':
            query = arguments['query']
            if not isinstance(query,str) or not 1 <= len(query) <= 300: raise ValueError('Invalid query')
            self.state.clear()  # New search invalidates downstream context.
            result = search_papers(query,self.live_search)
            self.state['papers'] = result
        elif name == 'method_extraction':
            result = extract_methods(self.state['papers'])
            self.state['methods'] = result
        elif name == 'configure_experiment':
            self.state['methods']  # Require cited methods before configuration.
            validate(arguments)
            for key in ('result','evaluation','report'): self.state.pop(key,None)
            result = dict(arguments)
            self.state['config'] = result
        elif name == 'python_experiment':
            result = run(self.state['config'])
            for key in ('evaluation','report'): self.state.pop(key,None)
            self.state['result'] = result
        elif name == 'evaluation':
            result = evaluate_result(self.state['result'])
            self.state['evaluation'] = result
        else:
            result = summary(self.state['methods'],self.state['result'],self.state['evaluation'])
            self.state['report'] = result
        self.trace.append({'step':len(self.trace)+1,'tool':name,'arguments':dict(arguments),'result':result})
        return result
