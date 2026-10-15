"""Inspect audit artifacts and optionally plot the measured workflow timings."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research_agent.benchmark import report

p=argparse.ArgumentParser()
p.add_argument('folder',type=Path)
args=p.parse_args()
out=args.folder
metadata=json.loads((out/'benchmark.json').read_text())
runs=metadata['runs']
if len(runs)!=2*len(metadata['tasks']): raise ValueError('All predeclared attempts must be present')
report(out,metadata,runs)
observations=['','## 原始记录复核与工具错误','']
for r in runs:
    folder=out/r['task_id']/r['controller']
    attempts=json.loads((folder/'tool-attempts.json').read_text())
    model_trace=json.loads((folder/'model-trace.json').read_text())
    protocol=json.loads((folder/'mcp-protocol.json').read_text())
    assert len(attempts)==r['attempted_tool_calls']
    assert len(model_trace)==r['model_rounds']
    assert sum(not a['ok'] for a in attempts)==r['failed_tool_calls']
    calls=[x for x in protocol if x['direction']=='request' and x['message']['method']=='tools/call']
    assert len(calls)==len(attempts)
    if r['controller']=='local_llm':
        assert r['model_rounds']==r['attempted_tool_calls']+r['parse_failures']
        for event in model_trace:
            assert isinstance(event['raw_output'],str)
            assert event['prompt_tokens']>0 and event['completion_tokens']>0
    for i,a in enumerate(attempts):
        if not a['ok']:
            recovery='后续最终完成任务' if r['task_success'] else '后续未满足全部任务条件'
            observations.append(f"- {r['task_id']} / {r['controller']}，工具尝试 {i+1}：`{a['tool']}` → `{a['error']}`；{recovery}。详见其 model-trace.json 与 MCP 原始响应。")
for task in metadata['tasks']:
    records=[r for r in runs if r['task_id']==task['id']]
    if all(r['task_success'] for r in records):
        a=json.loads((out/task['id']/'fixed/metrics.json').read_text())
        b=json.loads((out/task['id']/'local_llm/metrics.json').read_text())
        assert a==b
        observations.append(f"- {task['id']}：两个调度器的全部数值实验结果完全一致。改进点是工具调用能力，不是预测模型性能。")
observations += ['- 任务通过标准只要求非空的实时论文证据，尚未评价检索相关性或是否精确命中原论文。关键词结果含引用该模型的后续论文，不能称作精确论文定位。',
                 '- 首次启动在模型元数据初始化处失败，尚未执行任何任务；setup-failure/ 中保留该错误和日志。修复 Transformers 版本兼容后，保持任务与提示不变执行完整实验。']
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,4))
    ids=[t['id'] for t in metadata['tasks']]
    for j,controller in enumerate(('fixed','local_llm')):
        values=[next(r['elapsed_seconds'] for r in runs if r['task_id']==ident and r['controller']==controller) for ident in ids]
        ax.bar([i+(j-.5)*.35 for i in range(len(ids))],values,width=.35,label=controller)
    ax.set_xticks(range(len(ids)),ids)
    ax.set_yscale('log')
    ax.set(ylabel='Task seconds (log scale)',title='Actual workflow time: local Qwen + MCP vs fixed + MCP')
    ax.legend(); fig.tight_layout(); fig.savefig(out/'workflow-time.png',dpi=160); plt.close(fig)
    observations += ['','![Measured workflow time](workflow-time.png)']
except ImportError:
    observations.append('- 未安装 matplotlib，跳过可选耗时图。')
with (out/'REPORT.md').open('a',encoding='utf-8') as f:
    f.write('\n'.join(observations)+'\n')
print('All task artifacts checked; report updated.')
