# Model Card — AI Predictive Maintenance: Failure-Within-H Model

**Version:** `cmapss-fd001-h30-20261001T203719Z`  |  **Training timestamp (UTC):** 2026-10-01T20:37:19+00:00  |  **Evaluation date (UTC):** 2026-10-01T20:37:56+00:00

## Model purpose
Estimate P(failure within the next 30 operating cycles) per machine and cycle, plus an anomaly score, a deterministic Machine Health Indicator (0-100), a data-quality status and a rule-based AI recommendation.

## Dataset
NASA C-MAPSS **FD001** — a **simulated turbofan-engine run-to-failure benchmark**. Sensor columns `sensor_1`-`sensor_21` are **anonymized**; no physical meaning is assigned. It is not motor, pump or compressor data. Train file: 100 units / 20,631 rows; official test: 100 units / 13,096 rows.

## Target and failure horizon
`failure_within_h` = 1 if remaining useful life <= **H = 30 cycles**, else 0. Train positive rate: 0.152.
**Why H = 30? (configured, not optimized)** H is a configured planning lead time (in operating cycles) chosen before modelling as a business parameter. It was NOT optimised on validation or test performance, and no sensitivity study over other H values was run. Re-run the notebook with another FAILURE_HORIZON_H to compare.

## Features (115)
Per-unit **causal** features: raw active sensors (14), non-constant operating settings (2), cycle number, rolling mean/std (windows [5, 10]), 1-cycle difference and safe percentage change, and 10-cycle slope. Dropped (constant/low variance in training units): ['sensor_1', 'sensor_5', 'sensor_6', 'sensor_10', 'sensor_16', 'sensor_18', 'sensor_19', 'operating_setting_3'].

## Training methodology
* Units split into train/validation/internal-test **by `unit_id`** (60/20/20); the official test file is a second unseen set.
* Candidates: logistic regression, HistGradientBoosting, XGBoost. Selected by validation PR-AUC (tie-break: Brier) -> **xgboost**. Class weighting used: False.
* Probability calibration: **sigmoid**, chosen by grouped out-of-fold Brier on validation units.
* Anomaly detector: Isolation Forest trained on healthy training rows (RUL >= 100); alarm threshold recalibrated on healthy validation rows (measured healthy flag rate on unseen internal-test units: 2.78% vs target 2.0%).
* Decision threshold **0.10** (max F2 on validation).

## Metrics (measured in this run; threshold 0.10)
| Set | Precision | Recall | F1 | ROC-AUC | PR-AUC | Brier | ECE |
|---|---|---|---|---|---|---|---|
| Validation (out-of-fold calibrated) | 0.685 | 0.961 | 0.800 | 0.989 | 0.945 | 0.0287 | 0.009 |
| Internal test (unseen units) | 0.692 | 0.968 | 0.807 | 0.991 | 0.962 | 0.0245 | 0.007 |
| Official test_FD001 (all rows) | 0.591 | 0.852 | 0.698 | 0.993 | 0.816 | 0.0102 | 0.005 |

Full metrics incl. accuracy: `evaluation/metrics.json`; curves and bins: `evaluation/curves.json`.

## Prediction interpretation
* failure_probability is a calibrated ESTIMATE, not a guarantee; calibration quality is measured, not assured.
* anomaly_score is a percentile rank versus healthy reference data, not a probability; an anomaly is not a failure.
* machine_health_indicator is a deterministic formula, not a trained model and not a physical measurement.
* data_quality_status is independent of the prediction; DATA_INVALID inputs are not scored.
* Recommendations are AI-generated, rule-based (no LLM) and are not a confirmed diagnosis.

Data quality mapping: `DATA_OK` = reliable, `DATA_WARNING` = reliability reduced, `DATA_INVALID` = not scored.

## Intended use
* Portfolio/MVP demonstration of an end-to-end predictive-maintenance ML pipeline
* Decision support on C-MAPSS-style multivariate run-to-failure data

## Non-intended use
* Safety-critical or real maintenance decisions
* Real aircraft engines
* Machine types or sensor layouts not matching the trained schema
* Automated maintenance actions without human review

## Known limitations
* Trained and evaluated on a SIMULATED single-operating-condition dataset (FD001); results may not transfer to real machines or other C-MAPSS subsets.
* Small number of engines; metrics carry sampling uncertainty (unit-to-unit variability is large).
* The `cycle` feature lets the model use machine age; this helps on this benchmark but may not generalise.
* Explanations describe model behaviour, not physical causes (sensors are anonymized).
* The anomaly detector is unsupervised and evaluated only via a proxy (healthy vs near-failure rows).
* The out-of-distribution check is a simple range check.
* Failure horizon H=30 is configured, not optimized; no sensitivity study over H was run.
