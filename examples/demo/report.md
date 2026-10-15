# Research Agent 实验报告

本次运行真实执行了 Python 合成数据实验；论文笔记用于研究背景，未复现所引用论文模型。

## 文献来源

- [A Time Series is Worth 64 Words: Long-term Forecasting with Transformers](https://arxiv.org/abs/2211.14730) — `bundled_method_note_not_live_search`
  - 方法证据：This bundled human-written method note describes PatchTST: partition time series into patches and use channel-independent Transformer modeling. It is not a fetched abstract.
- [Chronos: Learning the Language of Time Series](https://arxiv.org/abs/2403.07815) — `bundled_method_note_not_live_search`
  - 方法证据：This bundled human-written method note describes Chronos: scale and quantize time series into tokens, then train language models for probabilistic forecasting. It is not a fetched abstract.

## 实验配置

```json
{
  "seed": 42,
  "context": 24,
  "horizon": 6,
  "ridge": 1.0
}
```

数据：`synthetic_periodic_v1`；先切分时间轴，再构造窗口；仅用训练段拟合归一化。
窗口数量：{'train': 176, 'val': 56, 'test': 56}。

| 模型 | Validation MSE | Test MSE | Test MAE |
|---|---:|---:|---:|
| persistence | 0.405151 | 0.426927 | 0.509413 |
| ridge_ar | 0.013330 | 0.014485 | 0.097750 |

验证集选出的模型：`ridge_ar`。
Ridge AR 相对 persistence 的测试 MSE 降幅：96.61%。

## 局限

- Synthetic data only; not a paper reproduction.
- Single seed; no statistical significance claim.
- Ridge autoregression is not PatchTST or another foundation model.
