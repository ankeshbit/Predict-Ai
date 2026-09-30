# Google Colab Training Notebook Contract (Gate H1)

This contract defines the exact interface between your Google Colab training notebook and the Predict-Ai platform.
The platform backend and evaluation engine strictly depend on the contracts provided by `pdm_core`.

---

## 1. Environment & Setup in Colab

In the first cell of your Google Colab notebook, install `pdm_core` directly from the repository:

```python
# Clone repository and install shared pdm_core in editable mode
!git clone https://github.com/ankeshbit/Predict-Ai.git
%cd Predict-Ai
!pip install -e ml/
```

Verify your Colab environment pins against `ml/constraints.txt` (especially `numpy==1.26.4`, `scikit-learn==1.4.2`, and `xgboost==2.0.3`).

---

## 2. Mandatory Imports from `pdm_core`

Your notebook should import the following tested helpers from `pdm_core` to prevent training/serving skew:

```python
# 1. Data loading and ground-truth RUL derivation
from pdm_core.data import (
    load_fd001_raw,
    compute_train_rul,
    compute_test_rul,
    CANONICAL_COLUMNS,
    UNIT_COL,
    CYCLE_COL,
)

# 2. Binary labeling over prediction horizon H
from pdm_core.labels import assign_binary_labels

# 3. Past-only, causal feature engineering (identical in training and serving)
from pdm_core.features import (
    extract_features,
    get_feature_names,
    load_feature_config,
)

# 4. Engine-grouped splitting (guarantees zero engine overlap)
from pdm_core.splits import engine_grouped_split

# 5. Metric computation & curves downsampled to <=50 points
from pdm_core.evaluation import (
    compute_evaluation,
    save_evaluation_json,
)

# 6. TreeSHAP & feature attribution
from pdm_core.explain import (
    compute_tree_shap,
    compute_linear_contribution,
    compute_feature_attributions,
)

# 7. Bundle serialization and integrity validation
from pdm_core.bundle import (
    write_complete_bundle,
    write_failure_risk_bundle,
    write_anomaly_bundle,
    validate_model_bundle,
)

# 8. Strongly typed Pydantic contracts
from pdm_core.schemas import (
    EvaluationSchema,
    ManifestSchema,
    ModelCardSchema,
)
```

---

## 3. End-to-End Workflow Template

```python
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb

# Step 1: Load NASA C-MAPSS FD001 data
train_df = load_fd001_raw("train_FD001.txt")
test_df = load_fd001_raw("test_FD001.txt")
rul_vector = np.loadtxt("RUL_FD001.txt")

# Step 2: Compute per-cycle RUL
train_df = compute_train_rul(train_df, max_rul_cap=125)
test_df = compute_test_rul(test_df, rul_vector, max_rul_cap=125)

# Step 3: Assign binary target label (e.g. H = 30 cycles)
H = 30
train_df = assign_binary_labels(train_df, horizon=H)
test_df = assign_binary_labels(test_df, horizon=H)

# Step 4: Extract causal past-only features
feature_df = extract_features(train_df)
test_feature_df = extract_features(test_df)
feature_names = get_feature_names()

# Step 5: Grouped split (engines never leak across folds)
train_split, val_split = engine_grouped_split(feature_df, test_size=0.20, random_state=42)

X_train, y_train = train_split[feature_names], train_split["label"]
X_val, y_val = val_split[feature_names], val_split["label"]
X_test, y_test = test_feature_df[feature_names], test_feature_df["label"]

# Step 6: Fit preprocessing strictly on train
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

# Step 7: Train and Calibrate Model (e.g. XGBoost + Platt scaling / sigmoid calibration)
base_clf = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.05,
    eval_metric="logloss",
    random_state=42
)
base_clf.fit(X_train_scaled, y_train)

# Calibrate probabilities on the held-out validation engines
calibrator = CalibratedClassifierCV(estimator=base_clf, method="sigmoid", cv="prefit")
calibrator.fit(X_val_scaled, y_val)

# Step 8: Evaluate on Test engines
test_probs = calibrator.predict_proba(X_test_scaled)[:, 1]

eval_schema = compute_evaluation(
    y_true=y_test,
    y_prob=test_probs,
    model_name="XGBoost Calibrated Failure Classifier",
    model_version="1.0.0",
    task="failure_risk",
    threshold=0.50,
    feature_names=feature_names,
    importances=base_clf.feature_importances_,
    methodology="Trained on 80 engines, calibrated on 20 validation engines, evaluated on 100 test engines.",
    limitations=[
        "Trained exclusively on C-MAPSS FD001 single-condition simulated turbofan telemetry.",
        "Output is statistical failure probability over 30 cycles, not a physical diagnostic.",
    ]
)

# Step 9: Assemble Model Card
model_card = ModelCardSchema(
    model_name="XGBoost Failure Risk Classifier",
    version="1.0.0",
    description="Gradient-boosted decision tree classifier with Platt calibration for 30-cycle turbofan failure risk.",
    model_type="xgboost",
    intended_use="Predictive maintenance decision support for turbofan fleet management.",
    domain="Simulated Turbofan Degradation (NASA C-MAPSS FD001)",
    training_dataset="NASA C-MAPSS FD001 Train (100 engines)",
    evaluation_dataset="NASA C-MAPSS FD001 Test (100 engines)",
    feature_summary=feature_names,
    hyperparameters={"n_estimators": 100, "max_depth": 4, "learning_rate": 0.05},
    operational_limitations=[
        "Sea-level operational conditions only.",
        "Requires 30 consecutive operating cycles for full feature window maturity.",
    ],
    ethical_considerations=[
        "AI recommendations must be reviewed and authorized by a qualified engineer before maintenance execution.",
    ],
    author="Human ML Engineer",
    created_at="2026-10-01T00:00:00Z"
)

# Compute reference baseline statistics (medians and MADs on training data)
reference_stats = {
    col: {
        "median": float(np.median(X_train[col])),
        "mad": float(np.median(np.abs(X_train[col] - np.median(X_train[col])))),
        "p1": float(np.percentile(X_train[col], 1)),
        "p99": float(np.percentile(X_train[col], 99)),
    }
    for col in feature_names
}

# Select ~20 held-out test engines for demo_candidates.csv
demo_units = test_df["unit_id"].unique()[:20]
demo_candidates_df = test_df[test_df["unit_id"].isin(demo_units)][CANONICAL_COLUMNS]

# Step 10: Serialize Complete Bundle
bundle_dir = write_complete_bundle(
    target_root=".",
    version="1.0.0",
    feature_config_content=load_feature_config(),
    demo_candidates_df=demo_candidates_df,
    failure_risk_kwargs={
        "model": base_clf,
        "preprocessing": scaler,
        "calibrator": calibrator,
        "reference_stats": reference_stats,
        "explainer_config": {"model_type": "xgboost", "explainer_kind": "tree_shap"},
        "model_card": model_card,
        "evaluation": eval_schema,
        "input_features": feature_names,
        "horizon": H,
        "decision_threshold": 0.50,
        "model_type": "xgboost",
    }
)

# Step 11: Validate bundle contracts before handoff
result = validate_model_bundle(bundle_dir)
assert result.valid is True, f"Bundle validation failed: {result.errors}"
print(f"[+] Bundle validated successfully at: {bundle_dir}")
```

---

## 4. Exported Bundle Structure (Gate H1 Artifact)

Your export will produce the directory `bundle_1.0.0/`:

```
bundle_1.0.0/
├── feature_config.yaml            # Pipeline feature definitions
├── demo_candidates.csv            # ~20 held-out test engines for seed mode
├── EXPORT_README.md               # Registration commands and checksum manifest
└── failure_risk/
    ├── manifest.json              # Version, task, SHA-256 hashes, library versions
    ├── model.joblib               # Fitted estimator
    ├── preprocessing.joblib       # Fitted scaler / imputer
    ├── calibrator.joblib          # Platt / Isotonic calibrator
    ├── reference_stats.json       # Feature baseline statistics
    ├── explainer_config.json      # Explainer configuration
    ├── model_card.json            # Model card metadata
    └── evaluation.json            # Downsampled curves, PR-AUC, Brier score, ECE
```

---

## 5. Verification Command for Handoff

Before handing the bundle to Phase 4 for registration into the platform, run:

```bash
python -m pdm_core.bundle validate backend/model_artifacts/bundle_1.0.0
```
