# Research Agent 实验报告

本次运行真实执行了 Python 合成数据实验；论文笔记用于研究背景，未复现所引用论文模型。

## 文献来源

- [LLM-Mixer: Multiscale Mixing in LLMs for Time Series Forecasting](http://arxiv.org/abs/2410.11674v2) — `live_arxiv_abstract`
  - 方法证据：Time series forecasting remains a challenging task, particularly in the context of complex multiscale temporal patterns. This study presents LLM-Mixer, a framework that improves forecasting accuracy through the combination of multiscale time-series decomposition with pre-trained LLMs (Large Language Models). LLM-Mixer captures both short-term fluctuations and long-term trends by decomposing the data into multiple temporal resolutions and processing them with a frozen LLM, guided by a textual prompt specifically designed for time-series data. Extensive experiments conducted on multivariate and univariate datasets demonstrate that LLM-Mixer achieves competitive performance, outperforming recent state-of-the-art models across various forecasting horizons. This work highlights the potential of combining multiscale analysis and LLMs for effective and scalable time-series forecasting.
- [Forecasting intermittent time series with Gaussian Processes and Tweedie likelihood](http://arxiv.org/abs/2502.19086v5) — `live_arxiv_abstract`
  - 方法证据：We adopt Gaussian Processes (GPs) as latent functions for probabilistic forecasting of intermittent time series. The model is trained in a Bayesian framework that accounts for the uncertainty about the latent function. We couple the latent GP variable with two types of forecast distributions: the negative binomial (NegBinGP) and the Tweedie distribution (TweedieGP). While the negative binomial has already been used in forecasting intermittent time series, this is the first time in which a fully parameterized Tweedie density is used for intermittent time series. We properly evaluate the Tweedie density, which has both a point mass at zero and heavy tails, avoiding simplifying assumptions made in existing models. We test our models on thousands of intermittent count time series. Results show that our models provide consistently better probabilistic forecasts than the competitors. In particular, TweedieGP obtains the best estimates of the highest quantiles, thus showing that it is more flexible than NegBinGP.
- [Probabilistic Hierarchical Forecasting with Deep Poisson Mixtures](http://arxiv.org/abs/2110.13179v8) — `live_arxiv_abstract`
  - 方法证据：Hierarchical forecasting problems arise when time series have a natural group structure, and predictions at multiple levels of aggregation and disaggregation across the groups are needed. In such problems, it is often desired to satisfy the aggregation constraints in a given hierarchy, referred to as hierarchical coherence in the literature. Maintaining coherence while producing accurate forecasts can be a challenging problem, especially in the case of probabilistic forecasting. We present a novel method capable of accurate and coherent probabilistic forecasts for time series when reliable hierarchical information is present. We call it Deep Poisson Mixture Network (DPMN). It relies on the combination of neural networks and a statistical model for the joint distribution of the hierarchical multivariate time series structure. By construction, the model guarantees hierarchical coherence and provides simple rules for aggregation and disaggregation of the predictive distributions. We perform an extensive empirical evaluation comparing the DPMN to other state-of-the-art methods which produce hierarchically coherent probabilistic forecasts on multiple public datasets. Comparing to existing coherent probabilistic models, we obtain a relative improvement in the overall Continuous Ranked Probability Score (CRPS) of 11.8% on Australian domestic tourism data, and 8.1% on the Favorita grocery sales dataset, where time series are grouped with geographical hierarchies or travel intent hierarchies. For San Francisco Bay Area highway traffic, where the series' hierarchical structure is randomly assigned, and their correlations are less informative, our method does not show significant performance differences over statistical baselines.

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
