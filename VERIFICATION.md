# 实际验证记录

日期：2026-10-15；Python 3.12，运行无需第三方依赖。

## 通过

- `python -m unittest discover -s tests -v`：5/5 通过。
- 离线演示：六步全部执行；输出保存在 `examples/demo/`。
- 真实 arXiv API：在命令获网络权限后，六步全部执行；输出保存在 `examples/live-arxiv/`。
- 独立 MCP 子进程测试：initialize、notifications/initialized、tools/list 与六次 tools/call。
- LLM 调度测试：使用模拟 API 返回的 function calls，确实调用本地工具、训练和生成报告；不是一次真实 LLM 调用。
- 测试覆盖非法工具/参数拒绝、前置状态要求、上下文失效、固定种子可重复，以及报告数字与结果一致。

## 实测配置与结果

数据 synthetic_periodic_v1；seed=42；context=24；horizon=6；ridge=1.0。

| 模型 | Test MSE | Test MAE |
|---|---:|---:|
| Persistence | 0.4269270926 | 0.5094125022 |
| Ridge AR | 0.0144845516 | 0.0977503629 |

联网和离线运行使用相同固定实验，所以指标一致；论文检索结果不会自动变成对应论文的模型代码。

## 未验证 / 未实现

- 真实 LLM API 调用、模型规划成功率、token 成本统计。
- 桌面 MCP 客户端兼容性；当前只有自有 stdio 协议集成测试。
- 论文全文解析、准确超参数提取、公开数据 benchmark 和论文原始指标复现。
- GitHub Actions 远端执行；只配置了 workflow。

初次联网被命令网络沙箱拒绝，授权联网重试成功。失败记录保存在本地 runs/，未当作成功示例。
