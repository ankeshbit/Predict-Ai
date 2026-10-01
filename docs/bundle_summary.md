# Production Model Bundle Summary

**Model Version:** `cmapss-fd001-h30-20261001T203719Z`  
**Training Platform:** Kaggle (`/kaggle/working/artifacts`)  
**Evaluation Date (UTC):** `2026-10-01T20:37:56+00:00`  
**Authoritative Runtime:** Python 3.12.13 (numpy 2.0.2, pandas 2.3.3, scikit-learn 1.6.1, scipy 1.16.3, joblib 1.5.3, xgboost 3.2.0, shap 0.51.0)

---

## 1. Verbatim `final_summary.txt`

```text
================================ FINAL ML SUMMARY ================================
Dataset                : NASA C-MAPSS FD001 (simulated turbofan benchmark; sensors anonymized)
Machines (train file)  : 100  -> train/val/internal-test units = 60/20/20
Machines (official test): 100
Observations           : train file 20,631 rows | official test 13,096 rows
Features used          : 115 (14 active anonymized sensors, 2 operating settings, cycle, rolling/diff/pct/slope features)
Failure horizon H      : 30 operating cycles - configured, NOT optimized   (train positive rate 0.152; class weighting: False)
Anomaly detection      : IsolationForest (healthy rows RUL>=100), target flag rate 2.0%; healthy flag rate on unseen internal-test units 2.78% (alarm threshold recalibrated on healthy validation rows)
Failure model          : xgboost (XGBClassifier)
Calibration            : sigmoid
Selected threshold     : 0.10  (max F2 on validation)
Internal-test metrics  : ROC-AUC 0.991 | PR-AUC 0.962 | Brier 0.0245 | ECE 0.007 | precision 0.692 | recall 0.968 | F1 0.807 | accuracy 0.930
Official-test metrics  : ROC-AUC 0.993 | PR-AUC 0.816 | Brier 0.0102 | ECE 0.005 | precision 0.591 | recall 0.852 | F1 0.698
Model version          : cmapss-fd001-h30-20261001T203719Z
Evaluation date (UTC)  : 2026-10-01T20:37:56+00:00
Library versions       : {'python': '3.12.13', 'numpy': '2.0.2', 'pandas': '2.3.3', 'scikit-learn': '1.6.1', 'scipy': '1.16.3', 'joblib': '1.5.3', 'xgboost': '3.2.0', 'shap': '0.51.0'}
Demo engines (seed 2024): [29, 48, 70, 77, 97]
Artifacts              : /kaggle/working/artifacts
Reload test            : verified + loaded in a fresh process (max diff vs in-memory 0.00e+00); tampering and version mismatch are refused

Known limitations      : simulated single-condition dataset; few engines -> uncertain estimates; anonymized sensors (no physical
                         interpretation); H not optimized; health indicator is a formula, not a measurement; recommendations are
                         AI-generated, not a confirmed diagnosis; calibration and thresholds should be re-validated on any new data.
=================================================================================
```

---

## 2. Causality and Leakage Test Proofs

From the Kaggle training notebook (`ml/notebooks/AI_Predictive_Maintenance_CMAPSS_FD001.ipynb`):

### Causality (No-Future-Information) Verification (Cell 25–26 & 35)
> *"Causality (no-future-information) test. We verify by experiment that (1) truncating a unit's history at cycle k leaves the features at cycle k unchanged, (2) corrupting all future rows does not change features at cycle k, and (3) using only the last max_lookback rows reproduces the latest row's features exactly (this is what the backend will rely on)."*

Code assertion executed during training:
```python
_u = train_df[train_df.unit_id == train_units[0]]
_a = feature_engineer.transform(_u[_u.cycle <= 60])
_b = feature_engineer.transform(_u).loc[_a.index]
np.testing.assert_allclose(_a.to_numpy(), _b.to_numpy(), atol=1e-9)
```

### Shuffled-Label Negative Control (Cell 34–35)
> *"We verify: (1) no label-generation column is a feature, (2) no single feature is (almost) a perfect predictor of the label, (3) features are causal (re-tested with the final engineer), and (4) a negative control — a model trained on shuffled labels — scores no better than chance on validation. If the pipeline leaked labels or had severe target leakage, the shuffled control would achieve high PR-AUC."*

Code execution result during training:
```python
_rng = np.random.RandomState(RANDOM_STATE)
_ctrl = HistGradientBoostingClassifier(max_iter=100, random_state=RANDOM_STATE).fit(X_train, _rng.permutation(y_train))
_ctrl_ap = average_precision_score(y_val, _ctrl.predict_proba(X_val)[:, 1])
# Output: "Negative control (shuffled labels) validation PR-AUC = 0.152 vs prevalence = 0.152 (should be close)"
# Output: "Leakage checks passed."
```
