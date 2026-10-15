"""Predeclared tasks: actual local LLM+MCP versus fixed workflow+MCP."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import time
from .agent import demo
from .experiment import run
from .local_llm import LocalQwen, local_agent
from .mcp_client import MCPClient


def task_prompt(task):
    config = json.dumps(task['config'])
    return (f"Search arXiv for {task['paper_query']}. Extract the returned method evidence. "
            f"Configure and run the allowlisted synthetic periodic forecasting experiment using exactly {config}. "
            "Evaluate the measured results and create experiment_summary. Do not reproduce or claim to implement the retrieved paper. "
            "Call one tool at a time in the required workflow order.")


def save_session(folder,session,metadata):
    folder.mkdir(parents=True,exist_ok=False)
    files = {'run.json':metadata,'trace.json':session.trace,'model-trace.json':session.model_trace,
             'tool-attempts.json':session.attempts,'mcp-protocol.json':session.protocol_trace}
    if 'result' in session.state: files['metrics.json'] = session.state['result']
    for name,value in files.items():
        (folder/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    if 'report' in session.state: (folder/'report.md').write_text(session.state['report'],encoding='utf-8')


def execute(task,controller,backend):
    session = MCPClient(live_search=True)
    started = time.perf_counter()
    status,error = 'completed',None
    try:
        if controller == 'fixed': demo(session,task['paper_query'],task['config'])
        else: local_agent(session,task_prompt(task),backend)
    except Exception as exc:
        status,error = 'failed',f'{type(exc).__name__}: {exc}'
    elapsed = time.perf_counter()-started
    session.close()
    complete = status == 'completed' and 'report' in session.state
    config_match = session.state.get('config') == task['config']
    papers = session.state.get('papers',[])
    live_evidence = bool(papers) and all(p['source']=='live_arxiv_abstract' for p in papers)
    measured = session.state.get('result')
    # Recompute once from the recorded config to verify numerical report provenance.
    reproducible = measured == run(measured['config']) if measured else False
    success = complete and config_match and live_evidence and reproducible
    metadata = {'task_id':task['id'],'controller':controller,'status':status,'error':error,
        'prompt':task_prompt(task),'expected_config':task['config'],'elapsed_seconds':elapsed,
        'workflow_completed':complete,'config_match':config_match,'nonempty_live_evidence':live_evidence,
        'numerically_reproduced':reproducible,'task_success':success,
        'model_rounds':len(session.model_trace),'successful_tool_calls':len(session.trace),
        'failed_tool_calls':sum(not a['ok'] for a in session.attempts),'attempted_tool_calls':len(session.attempts),
        'parse_failures':sum(not a.get('parsed',True) for a in session.model_trace),
        'prompt_tokens':sum(a.get('prompt_tokens',0) for a in session.model_trace),
        'completion_tokens':sum(a.get('completion_tokens',0) for a in session.model_trace),
        'arxiv_ids':[p['id'] for p in papers]}
    if measured: metadata['test'] = measured['test']
    return session,metadata


def report(out,metadata,runs):
    n = len(metadata['tasks'])
    lines = ['# 真实本地 LLM + MCP 实验','',
        f"运行时间：{metadata['utc_started']}。模型：`{metadata['model']['model']}`，固定 revision `{metadata['model']['revision']}`。",'',
        '真实模型推理，真实 arXiv API，真实 stdio MCP 子进程，真实 Python 实验；未使用模拟 LLM 输出。',
        '本次执行和代码由 AI 助手完成；代码与产物公开供维护者独立复跑和核验。','',
        '## 预先固定的协议','',
        '- 3 个任务在运行前定义于 benchmarks/tasks.json，所有任务和失败均保留，无成功筛选。',
        '- 对照：固定六步工作流 + MCP；实验组：Qwen 根据工具 schema 生成调用 + MCP。两者均联网检索。',
        '- 系统提示已规定工具顺序；这是受约束的工具调度，不是开放式自主科研规划。',
        '- 每任务最多 12 轮，每轮最多 192 新 token；greedy，关闭 thinking，CPU float32，2 个线程。',
        '- 任务成功需同时满足：生成报告、配置严格匹配、非空实时论文证据，以及独立重算指标一致。',
        '- 方法证据仍是摘要原文保留，不包含全文理解；实验是合成周期信号 Ridge AR，并非论文模型复现。',
        '- Prompt token 为每轮完整输入 token 数之和；本地推理无 API token 账单。耗时含推理/网络/工具，不含模型首次下载与加载。','',
        '## 工作流结果','',
        '| 任务 | 调度方式 | 成功 | 模型轮数 | 工具成功/尝试 | 参数匹配 | 秒数 |',
        '|---|---|---|---:|---:|---|---:|']
    for r in runs:
        lines.append(f"| {r['task_id']} | {r['controller']} | {r['task_success']} | {r['model_rounds']} | {r['successful_tool_calls']}/{r['attempted_tool_calls']} | {r['config_match']} | {r['elapsed_seconds']:.2f} |")
    lines += ['', '## 聚合结果','']
    for controller in ('fixed','local_llm'):
        group=[r for r in runs if r['controller']==controller]
        successes=sum(r['task_success'] for r in group)
        attempts=sum(r['attempted_tool_calls'] for r in group)
        failures=sum(r['failed_tool_calls'] for r in group)
        tokens=sum(r['prompt_tokens']+r['completion_tokens'] for r in group)
        lines.append(f"- {controller}: 成功 {successes}/{n}，工具失败 {failures}/{attempts}，模型解析失败 {sum(r['parse_failures'] for r in group)}，总 token {tokens}，总任务时间 {sum(r['elapsed_seconds'] for r in group):.2f} 秒。")
    lines += ['', '## Python 实验指标','',
        '指标为训练集标准差归一化后的合成信号误差，不用于证明 Agent 的研究质量；应与工作流完成率分别理解。','',
        '| 任务 | 调度 | Persistence Test MSE | Ridge AR Test MSE | Ridge AR Test MAE |',
        '|---|---|---:|---:|---:|']
    for r in runs:
        if 'test' in r:
            scores=r['test']
            lines.append(f"| {r['task_id']} | {r['controller']} | {scores['persistence']['mse']:.6f} | {scores['ridge_ar']['mse']:.6f} | {scores['ridge_ar']['mae']:.6f} |")
    lines += ['', '## 失败与边界','']
    failures=[r for r in runs if not r['task_success']]
    if not failures: lines.append('- 这 3 个任务没有观察到任务失败；不能外推为通用 Agent 成功率 100%。')
    for r in failures: lines.append(f"- {r['task_id']} / {r['controller']}: {r['error'] or 'Unmet task criterion; inspect run.json'}. See its model-trace.json and tool-attempts.json.")
    lines += ['- 网络时延和固定执行顺序会影响耗时对比；样本量仅 3，未随机化执行顺序，无统计显著性结论。',
        '- 控制组显式给定配置，LLM 组需从提示提取配置；对照主要检查额外模型调用的成本与参数遵循。',
        '- 未测试长任务、PDF 方法理解、任意代码生成、工具发现泛化、提示注入鲁棒性或真实科研效率提升。',
        '- 论文内容不是实验代码来源；相同配置下两个调度器应得到相同数值，不能将低预测误差归因于 LLM。','',
        '## 产物与复跑','',
        '- 每个任务/调度目录：run.json、model-trace.json、tool-attempts.json、mcp-protocol.json、trace.json；完成实验时另存 metrics.json/report.md。',
        '- benchmark.json 包含版本、模型 commit、代码 commit、预定义任务与所有聚合原始记录；环境见 environment.txt。','',
        '```bash','pip install torch --index-url https://download.pytorch.org/whl/cpu',
        "pip install -e '.[local]'",'python -m research_agent.benchmark --out runs/local-mcp-replay','```']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',default='runs/local-mcp-20261015')
    p.add_argument('--model-cache',default=None)
    p.add_argument('--revision',default='c1899de289a04d12100db370d81485cdf75e47ca')
    args=p.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=False)
    tasks=json.loads(Path('benchmarks/tasks.json').read_text())
    metadata={'utc_started':datetime.now(timezone.utc).isoformat(),'tasks':tasks,
        'python':platform.python_version(),
        'code_revision':subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()}
    try:
        backend=LocalQwen(revision=args.revision,cache_dir=args.model_cache)
    except Exception as exc:
        metadata.update(status='setup_failed',error=f'{type(exc).__name__}: {exc}')
        (out/'benchmark.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        raise
    metadata['model']=backend.metadata
    runs=[]
    for task in tasks:
        for controller in ('fixed','local_llm'):
            print(f"Starting {task['id']} / {controller}",flush=True)
            session,record=execute(task,controller,backend)
            save_session(out/task['id']/controller,session,record)
            runs.append(record)
            print(json.dumps(record),flush=True)
            metadata['runs']=runs
            (out/'benchmark.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    metadata['utc_finished']=datetime.now(timezone.utc).isoformat()
    (out/'benchmark.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    report(out,metadata,runs)
    print(f"Report: {out/'REPORT.md'}",flush=True)

if __name__ == '__main__': main()
