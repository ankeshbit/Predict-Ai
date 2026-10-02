# Deviations from PRD v3.0

This document tracks all approved deviations between the verbatim PRD v3.0 specification (`docs/PRD.md`) and the implemented system, driven by empirical ML findings in the Kaggle (or Colab) training notebook (`AI_Predictive_Maintenance_CMAPSS_FD001.ipynb`).

---

## 1. Machine Health Indicator Formulation & Additive Breakdown

### PRD v3.0 Specification (§5 / FR-10)
PRD v3.0 specified a linear weighted sum with weights summing to 100%:
$$\text{Health Indicator} = 100 - (W_{\text{risk}} \cdot s_{\text{risk}} + W_{\text{anom}} \cdot s_{\text{anom}} + W_{\text{trend}} \cdot s_{\text{trend}})$$
Subject to constraint: $W_{\text{risk}} + W_{\text{anom}} + W_{\text{trend}} = 100\%$.

### Implemented Notebook-Driven Formulation
In the Kaggle (or Colab) ML pipeline (`ml/notebooks/AI_Predictive_Maintenance_CMAPSS_FD001.ipynb`), the linear weighted sum was replaced with a multiplicative interaction that decomposes into an additive penalty breakdown:
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
To provide rigorous transparency without conflating validation sets, the Kaggle (or Colab) pipeline evaluates and stores metrics for two distinct evaluation sets in `model_evaluations`:
1. **Internal Test Set**: 20 held-out engine trajectories from the C-MAPSS training set (unseen during model training and threshold tuning).
2. **Official C-MAPSS Test Benchmark (`test_FD001`)**: The standard 100-engine NASA benchmark test set scored against ground-truth remaining useful life (RUL) vectors.

Both sets store downsampled ROC, PR, and calibration curves ($\le 50$ points), confusion matrices, and metrics. Both are explicitly labelled and togglable on the Model Performance page.

---

## 4. Risk Bands Aligned with Decision Threshold & Explicit Alert Rule Thresholds

### PRD v3.0 Specification (§7 / FR-12, FR-14)
PRD v3.0 referenced generic default risk levels [0.20, 0.50] and fixed alert thresholds.

### Implemented Notebook-Driven Decision
The production XGBoost model selected on Kaggle has a calibrated decision threshold of **0.10** (optimizing validation $F_2$ with minimum precision 0.50). 
To align the UI and scoring semantics:
1. **Risk Bands Default Alignment**: `RiskBandsConfig` defaults are set to `low_max = 0.10`, `medium_max = 0.50`, `high_max = 0.80`. Any prediction with $P_{\text{fail}} \ge 0.10$ (the decision threshold) is classified as at least "Medium" risk, eliminating the contradiction where a prediction at the decision threshold was previously labelled "Low".
2. **Explicit Alert Rules**: The `high_failure_risk` alert threshold is dynamically queried from the active `alert_rules` table (`RULE_HIGH_FAILURE_RISK`, default threshold $0.50$, consecutive $N=3$) rather than being hardcoded in application logic or silently coupled to the decision threshold.

---

## 5. Five Demo Machines Seeded from Held-out Engines

### PRD v3.0 Specification (§8 / FR-18)
PRD v3.0 referenced seeding eight demo machines.

### Implemented Notebook-Driven Decision
The production Kaggle training pipeline evaluated and exported exactly five held-out test engines in `demo_units.csv` (`[29, 48, 70, 77, 97]`) with reference trajectories in `demo_reference_scores.csv`. 
Five demo machines are deterministically seeded to provide a balanced fleet of **2 Healthy, 2 Warning, 1 Critical**:
- **`ENGINE-070` (Healthy Demo)**: Truncated at early cycle 35 ($\text{HI} = 99.95$, early Excellent/Healthy cycle).
- **`ENGINE-097` (Healthy Demo)**: Truncated at early cycle 35 ($\text{HI} = 99.96$, early Excellent/Healthy cycle).
- **`ENGINE-077` (Warning Demo)**: Truncated at cycle 125 ($\text{HI} = 51.51$), chosen for having the widest Warning window (20 cycles with $51 \le \text{HI} \le 70$, span 99–134).
- **`ENGINE-029` (Warning Demo)**: Truncated at cycle 125 ($\text{HI} = 63.36$, health indicator in the 60–65 Warning range).
- **`ENGINE-048` (Critical Demo)**: Truncated at final cycle 231 ($\text{HI} = 0.75 \le 30$), leaving an open high-risk alert with recommendation snapshot.

---

## 6. Dependency Security Audit & Python Runtime Matrix (Accepted Risk)

### ML Artifact Pinned Dependencies
The model artifacts were fitted and serialized under Python 3.12.13 with exact pinned dependencies in `backend/requirements-inference.txt`:
```text
numpy==2.0.2
pandas==2.3.3
scikit-learn==1.6.1
scipy==1.16.3
joblib==1.5.3
xgboost==3.2.0
```

### Audit Findings & Accepted Risk
1. **Zero Vulnerabilities in Core Inference**: Running `pip-audit -r requirements-inference.txt --no-deps --disable-pip` against both PyPI and OSV vulnerability databases reports **0 known vulnerabilities** for all 6 pinned packages.
2. **Python >= 3.11 Constraint**: `scipy==1.16.3` strictly requires Python >= 3.11. Production deployment runs in Docker with Python 3.12.
3. **Immutability of Bundled Packages**: In accordance with PRD §1.4 (*Strict Separation of Training and Inference*), the backend never retrains or adjusts model weights. Changing serialized versions of `scikit-learn` or `scipy` without full retraining in Colab risks silent numerical drift or unpickling incompatibility. The versions in `requirements-inference.txt` are therefore accepted frozen dependencies.
