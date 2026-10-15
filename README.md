# Research Agent Lab · 自动化科研助手

可审计的 Research Agent 工程起点：论文检索 → 方法证据提取 → 工具选择 → Python 实验 → 评价 → 报告。Python 3.10+，默认仅使用标准库，无需 pip 安装依赖即可跑通。

**已实测离线与真实 arXiv 检索六步工具链，以及 MCP stdio 集成；真实 LLM API 调用尚未验证。默认 demo 是固定调度，不是 LLM 自主规划。**

## 快速运行

在解压后的项目根目录：

```bash
python -m unittest discover -s tests -v
python -m research_agent.cli --out runs/my-first-demo
```

Windows 如无 `python` 命令可替换为 `py`。输出目录必须尚不存在，避免覆盖原实验。

打开 `runs/my-first-demo/report.md` 查看报告。其他输出：

- `metrics.json`：实际计算的验证/测试指标、数据切分和配置。
- `trace.json`：六步工具输入与输出，方便重放检查。
- `run.json`：运行模式、查询、Python 版本与成功/失败状态。

仓库内 [examples/demo/report.md](examples/demo/report.md) 和相邻 JSON 是本环境实际执行得到的示例，不是手填指标。

## 三种运行方式

| 模式 | 论文来源 | 任务调度 | 验证状态 |
|---|---|---|---|
| 默认 demo | 两条明确标注的离线人工方法笔记 | 固定六步 | 已运行 |
| demo + `--live-search` | arXiv API 的前三条摘要 | 固定六步 | 已运行，见 examples/live-arxiv |
| `--mode llm` | 离线笔记或额外开启 live search | LLM function calling，最多 12 轮 | 模拟 API 测试通过，真实模型待验证 |

离线笔记包含真实论文标题、arXiv ID 与链接，但不是实时搜索结果，也不是论文原文摘要。方法提取目前保留摘要/笔记的原始证据，并标出缺失的训练配方、参数和代码 commit；尚未实现全文 PDF 解析与深入方法推理。

联网检索：

```bash
python -m research_agent.cli --live-search --query "time series forecasting transformer" --out runs/arxiv
```

arXiv 可能限流或不可达；错误会中止流程，并在 `run.json` 记录失败类型，不会悄悄冒充联网成功。

## 接入真实 LLM

本实现使用 OpenAI-compatible Chat Completions function calling。仅在你自己的终端设置密钥，不要提交到 GitHub 或发送到聊天中。调用会产生相应服务费用。

macOS/Linux：

```bash
export OPENAI_API_KEY='在本地填写你的密钥'
# 可选：export OPENAI_BASE_URL='https://api.openai.com/v1'
python -m research_agent.cli --mode llm --model gpt-4.1-mini --out runs/llm
```

Windows PowerShell：

```powershell
$env:OPENAI_API_KEY="在本地填写你的密钥"
python -m research_agent.cli --mode llm --model gpt-4.1-mini --out runs/llm
```

模型需支持 function calling；按账户可用模型修改 `--model`。更换 API 地址会将查询和工具结果发给对应提供商。不要直接使用示例中填写密钥的命令作为共享脚本。

LLM 每轮选择工具名与参数，工具返回结果写回上下文。缺失前置状态、未知工具或非法参数会作为错误反馈给模型。最终报告由结构化指标渲染，LLM 不直接填写实验数字。上下文目前保留整个有界工具对话，没有长期记忆、向量检索或压缩机制。

## MCP 接入

无需第三方 SDK，提供最小 MCP `2024-11-05` JSON-RPC stdio 服务，支持 `initialize`、`ping`、`tools/list`、`tools/call`。已通过真实子进程协议测试；尚未用某个桌面 MCP 客户端验证。非 HTTP 服务，不包含资源、prompt、认证与多租户功能。

在支持 stdio 的 MCP 客户端中配置（替换为你本机绝对路径）：

```json
{
  "mcpServers": {
    "research-agent": {
      "command": "python",
      "args": ["-m", "research_agent.mcp"],
      "cwd": "/absolute/path/to/research-agent"
    }
  }
}
```

如客户端不支持 `cwd`，先在项目目录 `pip install -e .`，再把 command 换成该 Python 环境下的 `research-mcp` 绝对路径并移除 args/cwd。联网服务器可在 args 最后加 `--live-search`。

可用工具按以下顺序调用，状态保存在单个服务进程内：

1. `paper_search(query)`
2. `method_extraction()`
3. `configure_experiment(seed, context, horizon, ridge)`
4. `python_experiment()`
5. `evaluation()`
6. `experiment_summary()`

新的检索会清除下游状态；修改实验配置会清除旧结果。CLI 的 LLM 分支直接使用相同的工具注册表，不是通过 MCP 客户端连接服务器；MCP 是给外部 Agent 使用的另一入口。

## 实验实际做了什么

固定生成 1800 点周期信号加高斯噪声；先按时间划分 1080/360/360 的训练、验证、测试段，再构造不跨边界的窗口；仅使用训练段拟合归一化。默认 context=24、horizon=6、seed=42、ridge=1。

比较末值持久预测与多步 Ridge AR。通过验证集 MSE 选模型，并展示两者的测试指标。测试窗口以 horizon 为步长，每个目标点在单个窗口中评价；输入窗口可以重叠。指标单位为训练标准差归一化后的信号单位。

本环境实测 Test MSE：persistence **0.426927**；Ridge AR **0.014485**。这不是 ECG、公开 benchmark、PatchTST 或 Chronos 的复现结果；也不能说明 Agent 相对人工科研的效率提升。

工具仅允许固定的小规模实验，不执行 LLM 生成的任意 Python/shell。参数限制 context≤48、horizon≤24；真实系统运行外部代码仍需独立沙箱。此项目没有声称现有进程是 OS 安全沙箱。

## 上传到你的 GitHub

项目仓库：https://github.com/YeY-zi/research-agent-lab 。从 GitHub 获取并运行：

```bash
git clone https://github.com/YeY-zi/research-agent-lab.git
cd research-agent-lab
python -m unittest discover -s tests -v
python -m research_agent.cli --out runs/my-first-demo
```

如需发布到其他账号，先新建空仓库，再修改以下 remote 地址执行：

```bash
git init
git add .
git commit -m "Add research agent tools, MCP server and verified demo"
git branch -M main
git remote add origin https://github.com/YeY-zi/research-agent-lab.git
git push -u origin main
```

使用你本机已登录的 GitHub 授权；GitHub 不接受账号密码作为 HTTPS Git 密码。也可使用 GitHub Desktop 的 Add Existing Repository → Publish Repository。不要提交 `.env`、密钥、个人数据或运行凭证。

## 后续研究路线

- 用真实 LLM 和真实 arXiv 检索记录一次端到端运行，统计成功率、工具错误率、token 和费用。
- 从摘要提取升级到可追溯的全文方法字段，人工核验参数和出处。
- 给特定论文加入官方代码 commit、数据版本和可重复实验脚本，区分 baseline 实验与论文复现。
- 引入多任务集、失败恢复和与固定工作流的对照，再研究 Agent 规划是否带来实际收益。

当前适合的项目描述：**实现科研助手原型，提供六类结构化工具和 MCP stdio 接口，完成合成时间序列实验与可追溯报告，真实 LLM 调度待验证。**
