# Deviations from PRD v3.0

This document tracks all approved deviations between the verbatim PRD v3.0 specification (`docs/PRD.md`) and the implemented system, driven by empirical ML findings in the Google Colab training notebook (`AI_Predictive_Maintenance_CMAPSS_FD001.ipynb`).

---

## 1. Machine Health Indicator Formulation & Additive Breakdown

### PRD v3.0 Specification (§5 / FR-10)
PRD v3.0 specified a linear weighted sum with weights summing to 100%:
$$\text{Health Indicator} = 100 - (W_{\text{risk}} \cdot s_{\text{risk}} + W_{\text{anom}} \cdot s_{\text{anom}} + W_{\text{trend}} \cdot s_{\text{trend}})$$
Subject to constraint: $W_{\text{risk}} + W_{\text{anom}} + W_{\text{trend}} = 100\%$.

### Implemented Notebook-Driven Formulation
In the Colab ML pipeline (`ml/notebooks/AI_Predictive_Maintenance_CMAPSS_FD001.ipynb`), the linear weighted sum was replaced with a multiplicative interaction that decomposes into an additive penalty breakdown:
$$\text{HI} = \operatorname{clip}\Big(100 \times (1 - P_{\text{fail}}) \times (1 - w_a \cdot s_{\text{anom}}) - \text{penalty}_{\text{DQ}}, \, 0, \, 100\Big)$$

Before clipping, the formula decomposes additively for clear UI explainability:
$$\text{HI} = 100 - \Delta_{\text{risk}} - \Delta_{\text{anom}} - \Delta_{\text{DQ}}$$

Where:
- $\Delta_{\text{risk}} = 100 \cdot P_{\text{fail}}$: Dominant penalty from calibrated failure probability at configured horizon $H=30$ ($HI \to 0$ as $P_{\text{fail}} \to 1$).
- $\Delta_{\text{anom}} = 100 \cdot (1 - P_{\text{fail}}) \cdot w_a \cdot s_{\text{anom}}$: Secondary penalty from unsupervised anomaly severity ($s_{\text{anom}} \in [0, 1]$). $w_a = \text{anomaly\_weight}$ represents the maximum health share anomaly alone can remove (default $0.30$), ensuring anomaly alone cannot drive health to zero without failure risk.
- $\Delta_{\text{DQ}}$: Data quality deduction ($10.0$ for `DATA_WARNING`, $0.0$ for `DATA_OK`). If `DATA_INVALID`, no health indicator is computed (`None`).
- Sensor trend term: Monotonic degradation slope penalty is marked as **"not enabled"** in this release.

---

## 2. Failure Prediction Horizon $H$ Configured, Not Optimized

### PRD v3.0 Specification (§7 / FR-3)
PRD v3.0 referenced finding the optimal prediction horizon $H$ based on operational lead time and model F1/PR-AUC curves.

### Implemented Notebook-Driven Decision
The failure prediction horizon $H = 30$ cycles is established as an operational parameter rather than an ML-optimized threshold. No hyperparameter sensitivity optimization over $H$ was executed; the model card explicitly declares this operational configuration constraint so end-users understand $H=30$ reflects maintenance planning lead time.

---

## 3. Two Evaluation Sets Labelled on the Model Performance Page

### PRD v3.0 Specification (§7 / FR-16, FR-17)
PRD v3.0 referenced reporting offline validation metrics against a single held-out evaluation dataset.

### Implemented Notebook-Driven Decision
To provide rigorous transparency without conflating validation sets, the Colab pipeline evaluates and stores metrics for two distinct evaluation sets in `model_evaluations`:
1. **Internal Test Set**: 20 held-out engine trajectories from the C-MAPSS training set (unseen during model training and threshold tuning).
2. **Official C-MAPSS Test Benchmark (`test_FD001`)**: The standard 100-engine NASA benchmark test set scored against ground-truth remaining useful life (RUL) vectors.

Both sets store downsampled ROC, PR, and calibration curves ($\le 50$ points), confusion matrices, and metrics. Both are explicitly labelled and togglable on the Model Performance page.
