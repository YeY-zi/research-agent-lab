# Research Agent 实验报告

本次运行真实执行了 Python 合成数据实验；论文笔记用于研究背景，未复现所引用论文模型。

## 文献来源

- [TimesNet: Temporal 2D-Variation Modeling for General Time Series Analysis](http://arxiv.org/abs/2210.02186v3) — `live_arxiv_abstract`
  - 方法证据：Time series analysis is of immense importance in extensive applications, such as weather forecasting, anomaly detection, and action recognition. This paper focuses on temporal variation modeling, which is the common key problem of extensive analysis tasks. Previous methods attempt to accomplish this directly from the 1D time series, which is extremely challenging due to the intricate temporal patterns. Based on the observation of multi-periodicity in time series, we ravel out the complex temporal variations into the multiple intraperiod- and interperiod-variations. To tackle the limitations of 1D time series in representation capability, we extend the analysis of temporal variations into the 2D space by transforming the 1D time series into a set of 2D tensors based on multiple periods. This transformation can embed the intraperiod- and interperiod-variations into the columns and rows of the 2D tensors respectively, making the 2D-variations to be easily modeled by 2D kernels. Technically, we propose the TimesNet with TimesBlock as a task-general backbone for time series analysis. TimesBlock can discover the multi-periodicity adaptively and extract the complex temporal variations from transformed 2D tensors by a parameter-efficient inception block. Our proposed TimesNet achieves consistent state-of-the-art in five mainstream time series analysis tasks, including short- and long-term forecasting, imputation, classification, and anomaly detection. Code is available at this repository: https://github.com/thuml/TimesNet.
- [Robust Taxi Fare Prediction Under Noisy Conditions: A Comparative Study of GAT, TimesNet, and XGBoost](http://arxiv.org/abs/2507.20008v1) — `live_arxiv_abstract`
  - 方法证据：Precise fare prediction is crucial in ride-hailing platforms and urban mobility systems. This study examines three machine learning models-Graph Attention Networks (GAT), XGBoost, and TimesNet to evaluate their predictive capabilities for taxi fares using a real-world dataset comprising over 55 million records. Both raw (noisy) and denoised versions of the dataset are analyzed to assess the impact of data quality on model performance. The study evaluated the models along multiple axes, including predictive accuracy, calibration, uncertainty estimation, out-of-distribution (OOD) robustness, and feature sensitivity. We also explore pre-processing strategies, including KNN imputation, Gaussian noise injection, and autoencoder-based denoising. The study reveals critical differences between classical and deep learning models under realistic conditions, offering practical guidelines for building robust and scalable models in urban fare prediction systems.
- [TimesNet-Gen: Deep Learning-based Site Specific Strong Motion Generation](http://arxiv.org/abs/2512.04694v3) — `live_arxiv_abstract`
  - 方法证据：Effective earthquake risk reduction relies on accurate site-specific evaluations, which require models capable of representing the influence of local site conditions on ground motion characteristics. We address strong ground motion generation from time-domain accelerometer records and introduce the TimesNet-Gen, a deep generative framework. In this framework, site-specific generation is directly achieved through a station-restricted, Dirichlet-based latent space resampling strategy, without relying on explicit conditioning inputs or dimensionality reduction. Pre-trained on the AFAD dataset via self-supervised learning, the frozen model demonstrates robust cross-regional generalization by successfully generating station-specific NGA-West2 records without any fine-tuning. Model performance is evaluated by comparing the distributions of generated and real records in the log-HVSR space, alongside the joint analysis of peak ground acceleration and fundamental site frequency. As a baseline, we construct a spectrogram-based conditional variational autoencoder (CVAE) explicitly formulated for station-specific latent space modeling. The results show strong station-wise alignment, consistent cross-regional ground motion synthesis, and a favorable comparison with a spectrogram-based conditional variational autoencoder baseline, demonstrating that the model empirically maintains the essential physical coupling between frequency content and peak amplitude. Our codes are available via https://github.com/brsylmz23/TimesNet-Gen.

## 实验配置

```json
{
  "seed": 44,
  "context": 12,
  "horizon": 6,
  "ridge": 0.1
}
```

数据：`synthetic_periodic_v1`；先切分时间轴，再构造窗口；仅用训练段拟合归一化。
窗口数量：{'train': 178, 'val': 58, 'test': 58}。

| 模型 | Validation MSE | Test MSE | Test MAE |
|---|---:|---:|---:|
| persistence | 0.384358 | 0.412801 | 0.502682 |
| ridge_ar | 0.062840 | 0.065746 | 0.209977 |

验证集选出的模型：`ridge_ar`。
Ridge AR 相对 persistence 的测试 MSE 降幅：84.07%。

## 局限

- Synthetic data only; not a paper reproduction.
- Single seed; no statistical significance claim.
- Ridge autoregression is not PatchTST or another foundation model.
