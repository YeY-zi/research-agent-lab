# Research Agent 实验报告

本次运行真实执行了 Python 合成数据实验；论文笔记用于研究背景，未复现所引用论文模型。

## 文献来源

- [Sensor-Specific Transformer (PatchTST) Ensembles with Test-Matched Augmentation](http://arxiv.org/abs/2510.21282v1) — `live_arxiv_abstract`
  - 方法证据：We present a noise-aware, sensor-specific ensemble approach for robust human activity recognition on the 2nd WEAR Dataset Challenge. Our method leverages the PatchTST transformer architecture, training four independent models-one per inertial sensor location-on a tampered training set whose 1-second sliding windows are augmented to mimic the test-time noise. By aligning the train and test data schemas (JSON-encoded 50-sample windows) and applying randomized jitter, scaling, rotation, and channel dropout, each PatchTST model learns to generalize across real-world sensor perturbations. At inference, we compute softmax probabilities from all four sensor models on the Kaggle test set and average them to produce final labels. On the private leaderboard, this pipeline achieves a macro-F1 substantially above the baseline, demonstrating that test-matched augmentation combined with transformer-based ensembling is an effective strategy for robust HAR under noisy conditions.
- [Enhanced forecasting of stock prices based on variational mode decomposition, PatchTST, and adaptive scale-weighted layer](http://arxiv.org/abs/2408.16707v1) — `live_arxiv_abstract`
  - 方法证据：The significant fluctuations in stock index prices in recent years highlight the critical need for accurate forecasting to guide investment and financial strategies. This study introduces a novel composite forecasting framework that integrates variational mode decomposition (VMD), PatchTST, and adaptive scale-weighted layer (ASWL) to address these challenges. Utilizing datasets of four major stock indices--SP500, DJI, SSEC, and FTSE--from 2000 to 2024, the proposed method first decomposes the raw price series into intrinsic mode functions (IMFs) using VMD. Each IMF is then modeled with PatchTST to capture temporal patterns effectively. The ASWL module is applied to incorporate scale information, enhancing prediction accuracy. The final forecast is derived by aggregating predictions from all IMFs. The VMD-PatchTST-ASWL framework demonstrates significant improvements in forecasting accuracy compared to traditional models, showing robust performance across different indices. This innovative approach provides a powerful tool for stock index price forecasting, with potential applications in various financial analysis and investment decision-making contexts.
- [CT-PatchTST: Channel-Time Patch Time-Series Transformer for Long-Term Renewable Energy Forecasting](http://arxiv.org/abs/2501.08620v4) — `live_arxiv_abstract`
  - 方法证据：Accurate forecasting of renewable energy generation is fundamental to enhancing the dynamic performance of modern power grids, especially under high renewable penetration. This paper presents Channel-Time Patch Time-Series Transformer (CT-PatchTST), a novel deep learning model designed to provide long-term, high-fidelity forecasts of wind and solar power. Unlike conventional time-series models, CT-PatchTST captures both temporal dependencies and inter-channel correlations-features that are critical for effective energy storage planning, control, and dispatch. Reliable forecasting enables proactive deployment of energy storage systems (ESSs), helping to mitigate uncertainties in renewable output, reduce system response time, and optimize storage operation based on location-specific flow and voltage conditions. Evaluated on real-world datasets from Denmark's offshore wind, onshore wind, and solar generation, CT-PatchTST outperforms existing methods in both accuracy and robustness. By enabling predictive, data-driven coordination of ESSs across integrated source-grid-load-storage systems, this work contributes to the design of more stable, responsive, and cost-efficient power networks.

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
