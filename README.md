# Research Agent Lab · 科研工具调用原型

论文检索 → 方法证据保留 → 实验配置 → Python 实验 → 评价 → 报告。提供直接调用和真实 stdio MCP 两种工具入口，以及固定工作流、OpenAI-compatible API、本地 Qwen 三种调度方式。

**最新真实本地 LLM + MCP 对照实验：[results/local-mcp-20261015/REPORT.md](results/local-mcp-20261015/REPORT.md)。**

代码和云端实验由 AI 编程助手协助完成。公开的是可复核的学习原型及实际运行证据，维护者应独立理解和复跑后再作为个人能力证明。

## 真实实验做了什么

- 模型：Qwen/Qwen3-0.6B，固定模型 commit，CPU float32，greedy decoding，关闭 thinking。
- 3 个任务在运行前定义于 `benchmarks/tasks.json`；全部运行结果与失败保留。
- 固定六步工作流 + MCP，与真实 Qwen 工具调度 + MCP 对照。
- 两组都调用真实 arXiv API 和独立 Python MCP 服务进程。
- 检查任务完成、配置遵循、工具错误、token 数和耗时；Python 指标独立重算核验。
- 初次模型初始化遇到 Transformers 5 私有属性兼容问题；失败日志和修复说明同样保存。

本次实测（仅 3 个预定义任务）：

| 调度方式 | 完成任务 | 成功工具调用 / 尝试 | 被拒绝调用 | 平均任务耗时 |
|---|---:|---:|---:|---:|
| 固定工作流 + MCP | 3/3 | 18/18 | 0 | 1.58 秒 |
| Qwen3-0.6B + MCP | 3/3 | 18/21 | 3 | 132.05 秒 |

三次错误均为跳过 evaluation、提前请求报告；MCP 返回前置状态错误后，模型自行补上 evaluation 并完成报告。没有用固定流程替模型修复。两个调度器在相同实验配置下得到完全一致的数值指标。

系统提示规定六步顺序，所以这验证的是受约束的模型工具调用，不是开放式科研规划。方法提取仍是摘要证据保留；Python 实验为固定合成信号上的 Ridge AR，**不是自动实现检索到的论文，也没有证明科研效率提升**。

## 无依赖演示

Python 3.10+，在仓库根目录运行：

```bash
python -m unittest discover -s tests -v
python -m research_agent.cli --out runs/demo-new
```

默认 demo 不调用模型，仅验证固定流程。离线来源为两条有明确标注的项目方法笔记，不是假装实时搜索或论文原文摘要。

联网固定工作流：

```bash
python -m research_agent.cli --live-search --transport mcp --out runs/fixed-mcp
```

输出目录必须尚不存在，避免覆盖历史。Windows 如无 `python` 可替换为 `py`。

## 本地 Qwen：无需 API 密钥

建议 Python 3.12、至少 8 GB 内存。首次需下载约 1.2 GB 模型；CPU 运行需要时间。

```bash
python -m venv .venv
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e '.[local]'
python -m research_agent.benchmark --out runs/local-mcp-replay
```

Windows 的普通 demo 可直接运行；本次 MCP 客户端使用 POSIX 管道选择器，Windows 上请使用 WSL 复跑 MCP 基准。本次只在 Linux 验证。

这会执行所有预定义任务及两种调度器。该 benchmark 固定模型 revision 为 `c1899de289a04d12100db370d81485cdf75e47ca`。可用 `--model-cache /your/cache/path` 指定模型缓存；模型权重不提交到 GitHub。

单独运行一个模型任务：

```bash
python -m research_agent.cli --mode local --transport mcp --live-search \
  --model Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca \
  --query 'Search arXiv for PatchTST, extract evidence, run the synthetic experiment with seed 42, context 24, horizon 6, ridge 1.0, evaluate and summarize.' \
  --out runs/local-single
```

本地推理是真实模型生成工具调用。解析失败或工具错误会反馈给模型，最多 12 轮；不会用固定流程替模型补齐剩余步骤。

## 外部 LLM API

支持 OpenAI-compatible Chat Completions function calling。仅在本机配置 `OPENAI_API_KEY`，可选 HTTPS 的 `OPENAI_BASE_URL`。不要发送密钥到聊天或提交到仓库；API 费用由提供商计费。

```bash
export OPENAI_API_KEY='在本地填写'
python -m research_agent.cli --mode llm --model gpt-4.1-mini --transport mcp --live-search --out runs/api-llm
```

Windows PowerShell 使用 `$env:OPENAI_API_KEY="在本地填写"`。外部 API 分支通过模拟 API 单元测试；本仓库的真实模型证据来自本地 Qwen，尚未验证真实 OpenAI API 调用。

## MCP

提供最小 MCP `2024-11-05` JSON-RPC stdio 服务，支持 `initialize`、`ping`、`tools/list`、`tools/call`。本次本地模型实验由自有 MCP 客户端真正连接服务进程；桌面客户端兼容性仍待单独验证。

```json
{
  "mcpServers": {
    "research-agent": {
      "command": "python",
      "args": ["-m", "research_agent.mcp", "--live-search"],
      "cwd": "/absolute/path/to/research-agent-lab"
    }
  }
}
```

如客户端不支持 cwd，先在项目目录 `pip install -e .`，再使用该环境 `research-mcp` 可执行文件的绝对路径。默认服务不联网，追加 `--live-search` 才启用实时检索。

工具按前置状态依次使用：

1. `paper_search(query)`：arXiv 前三条结果，或明确标注的离线方法笔记。
2. `method_extraction()`：保留摘要/笔记证据、引用及缺失字段，不执行全文推理。
3. `configure_experiment(seed, context, horizon, ridge)`：校验受控实验参数。
4. `python_experiment()`：执行固定 Ridge AR 与 persistence 实验。
5. `evaluation()`：从实际结果计算比较指标。
6. `experiment_summary()`：结构化渲染报告，LLM 不直接填写指标。

新检索清除下游状态；修改配置使旧结果失效。每个 MCP 服务进程保存单个会话，没有多租户隔离、HTTP 服务或长期记忆。本地模型看到的长摘要会截断为 600 字符并标注；完整证据仍保存在原始工具记录中。

## Python 实验范围

固定生成 1800 点周期信号加噪声，先按时间切为 1080/360/360 的训练/验证/测试，再构造窗口；归一化只使用训练段。比较末值预测与多步 Ridge AR，通过验证 MSE 选择模型。

低预测误差说明该受控数值实验的效果，不代表 Agent 的研究质量。相同配置的两个调度器应得到相同指标；模型负责工具调用，不负责发明更好的预测模型。

工具不执行任意模型生成的 Python 或 shell。context≤48、horizon≤24 控制计算规模；这不是对任意外部代码的 OS 安全沙箱。

## 审计产物

每个任务保存：

- `run.json`：成功/失败、参数匹配、耗时、调用数和 token 统计。
- `model-trace.json`：模型原始生成、解析结果和工具错误。
- `mcp-protocol.json`：初始化、工具发现、请求与响应。
- `tool-attempts.json`：所有工具尝试，包括失败。
- `trace.json`：成功工具的完整输入与结果。
- `metrics.json` / `report.md`：实际完成数值实验时的指标与报告。

基准根目录另存预定义任务、模型/代码版本、所有任务结果和总结。旧的 `examples/demo/`、`examples/live-arxiv/` 是早期固定流程证据，不能作为 LLM 实验结果。

## 后续问题

增加任务数量、随机化对照顺序、评估检索相关性与全文方法提取，研究长任务失败恢复，并与人工或更强模型比较。当前 3 个受约束任务不足以证明通用可靠性、模型自主研究能力或科研效率收益。

## 模型来源

[Qwen3-0.6B 模型与许可证](https://huggingface.co/Qwen/Qwen3-0.6B)。本仓库不分发模型权重。
