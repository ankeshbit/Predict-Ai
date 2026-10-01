# AI-Powered Predictive Maintenance & Machine Intelligence Platform
## Product Requirements Document (PRD v3.0 Final)

---

## 1. Executive Summary & Vision
**Predict-Ai** (internally branded **PrediCore**) is an industrial-grade, 100% software-based predictive maintenance analytics platform. It ingests machine sensor data, evaluates operational telemetry, detects anomalies, estimates calibrated failure probability over a defined prediction horizon $H$, and produces deterministic Machine Health Indicators to support human maintenance decisions.

### Core Value Proposition
- **Explainable & Trustworthy**: Clear attribution of why a machine is at risk without black-box opacity.
- **Human-in-the-Loop**: Strict boundaries separating statistical AI predictions, heuristic recommendations, engineer decisions, physical actions, and verified outcomes.
- **Disciplined ML Lifecycle**: Offline training in Google Colab; immutable, checksum-verified model bundles registered via CLI; zero training or fitting inside the web application.
- **Production Guardrails**: Inflexible compatibility gates that reject malformed or non-compliant datasets before scoring can occur.

---

## 2. Demonstration Domain & Terminology Rules

### 2.1 Demonstration Dataset
- **Primary Benchmark**: NASA C-MAPSS FD001 (Commercial Modular Aero-Propulsion System Simulation) — simulated run-to-failure degradation of turbofan engines under sea-level operating conditions.
- **Mandatory Disclosures**:
  - C-MAPSS FD001 is **simulated turbofan engine data**. It is **never** referred to as motor, pump, compressor, or real plant data.
  - Sensors must be identified exclusively by their original identifiers: `sensor_1` through `sensor_21`, and operating settings `op_setting_1` through `op_setting_3`. No invented physical semantics (e.g. "temperature", "vibration", "thermal stress") are permitted without a certified mapping adapter.
  - The UI must display the banner: `"Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"` and badge demo assets with `"Demo / Simulated Data"`.

### 2.2 Terminology Policy
| Approved Term | Prohibited Term in MVP | Rationale |
| :--- | :--- | :--- |
| **Failure Probability** ($P(\text{Fail} \mid H)$) | "Confidence" | Confidence implies epistemic certainty; probability is calibrated frequency over horizon $H$. |
| **Prediction Reliability** | "Accuracy" | Reliability evaluates input distance to training baseline, not ground truth accuracy. |
| **Machine Health Indicator** | "Health Measurement" / "Health Score" | Health is a derived composite indicator (0–100), not an ISO physical measurement. |
| **AI Recommendation** | "Diagnosis" / "Prescription" | Algorithms advise; only human engineers diagnose equipment and authorize maintenance. |

---

## 3. Four-Stage Lifecycle Separation (Data & UI)
The system must never conflate automated analysis with physical reality. All workflows enforce 4 chronological stages:
1. **AI Prediction**: Calibrated mathematical risk $P(\text{Fail} \le H)$ and unsupervised anomaly score $s_{\text{anom}}$.
2. **AI Recommendation**: Deterministic decision-support rule triggered by threshold breaches (e.g., rule `REC_HPT_INSPECT_01`).
3. **Engineer Decision & Physical Action**: Human authority response: *Accepted*, *Modified*, or *Declined* with mandatory engineering rationale, followed by logged maintenance action.
4. **Maintenance Outcome & Audit**: Verification cycle confirming whether the equipment returned to healthy telemetry baselines.

---

## 4. Roles and Permissions (RBAC)
The system supports exactly two roles:
1. **Engineer**:
   - Access fleet overview and telemetry workstations.
   - Inspect sensor trends, anomaly episodes, and SHAP attributions.
   - Acknowledge active alerts and record maintenance interventions and outcomes.
   - Read-only access to model performance and registry.
2. **Admin**:
   - All Engineer privileges.
   - Upload new datasets and execute schema mapping / compatibility checks.
   - Trigger offline scoring jobs.
   - Configure Machine Health Indicator weights ($W_{\text{risk}}, W_{\text{anom}}, W_{\text{trend}}$).
   - Configure alert firing rules and consecutive cycle noise filters.
   - Access full system audit logs and trigger demo data reset.

---

## 5. Machine Health Indicator Formulation (FR-10)
The Machine Health Indicator is a deterministic composite index on a 0–100 scale:
$$\text{Health Indicator} = 100 - (W_{\text{risk}} \cdot s_{\text{risk}} + W_{\text{anom}} \cdot s_{\text{anom}} + W_{\text{trend}} \cdot s_{\text{trend}})$$

Where:
- $W_{\text{risk}} = 50\%$: Penalty from calibrated failure probability at horizon $H=30$.
- $W_{\text{anom}} = 30\%$: Penalty from rolling unsupervised anomaly severity.
- $W_{\text{trend}} = 20\%$: Penalty from monotonic sensor degradation slope over the trailing 20 cycles.
- Constraint: $W_{\text{risk}} + W_{\text{anom}} + W_{\text{trend}} \equiv 100\%$. Any configuration where the sum differs from 100 is rejected with a validation error.

### Health Bands:
- **Excellent**: $86 - 100$
- **Healthy**: $71 - 85$
- **Warning**: $51 - 70$
- **Poor**: $31 - 50$
- **Critical**: $0 - 30$

---

## 6. Dataset Compatibility Gate (FR-6)
Prior to ingestion or inference, any uploaded dataset must pass 11 verification checks:
1. **Column Completeness**: All canonical columns required by the active feature config are mapped.
2. **Data Types**: Telemetry channels must be numeric (floating point or integer).
3. **Sequence Length**: Minimum consecutive window length $L \ge 30$ cycles per machine.
4. **Monotonic Cycle Ordering**: `cycle` must increment monotonically without negative leaps.
5. **No Duplicate Timestamps**: Unique `(unit_id, cycle)` pairs.
6. **Bounded Imputation**: Missing value rate per channel $\le 5\%$. Forward-fill bounded to $\le 3$ cycles.
7. **Value Range Enforcement**: Raw readings must lie within reasonable sensor bounds.
8. **Constant Column Check**: Constant sensor channels identified in training must remain constant.
9. **Covariance Shift**: Telemetry covariance divergence within acceptable Mahalanobis bounds.
10. **Unit ID Cardinality**: At least 1 unit with valid historical run.
11. **Hash Verification**: Schema mapping SHA-256 hash must match active model contract.

If any check fails, the dataset is marked `rejected_incompatible`, scoring returns HTTP `409 Conflict (DATASET_INCOMPATIBLE)`, and the UI displays an actionable **Expected / Found / How-to-Fix** table.

---

## 7. Model Governance & Performance Contract (FR-16, FR-17)
- **Zero Fabricated Metrics**: No metrics may be hardcoded or invented in frontend, backend, or seed scripts. If no evaluation record exists, the UI explicitly states: `"Model evaluation not available."`
- **Stored Evaluation Schema**: All metrics derive from `model_evaluations`:
  - **PR-AUC (Primary Metric)**: Precision-Recall Area Under Curve (mandatory for class-imbalanced run-to-failure data).
  - **ROC-AUC**: Receiver Operating Characteristic AUC.
  - **Precision & Recall** at threshold $\tau = 0.50$.
  - **F1 Score** (harmonic mean).
  - **Brier Score**: Quadratic calibration error (target $\le 0.10$ with Platt scaling).
  - **Confusion Matrix**: True Positive, False Positive, False Negative, True Negative counts.
  - **Downsampled Curves**: 50-point downsampled ROC, PR, and Calibration curves.
- **Model Card Integrity**: A model cannot be activated in production without a complete model card detailing target definition, input features, training split, calibration method, intended use, and stated operational limitations.

---

## 8. Responsible Use & Disclosures (PRD §6)
1. The platform is an analytical decision-support system, not a safety-critical autopilot or physical control mechanism.
2. Predictions are statistical probabilities over a finite horizon $H$; they do not guarantee machine survival or pinpoint exact mechanical failure moments.
3. Recommendations require qualified human engineer authorization before work orders are issued.
4. Public benchmark demonstrations (C-MAPSS FD001) do not represent certified field deployments for flight hardware.

---

## 9. Telemetry Schema & Mapping Contract (PRD §8.4)
- **C-MAPSS Canonical Channels**:
  - Identifiers: `unit_id`, `cycle`, `op_setting_1`...`op_setting_3`, `sensor_1`...`sensor_21`.
  - No physical semantics or invented engineering units (`no physical_meaning`).
- **Schema Mapping Hash (`schema_mapping_hash`)**:
  - Deterministic SHA-256 hash of mapped source to canonical column bindings.
  - Recorded in dataset versioning and immutable prediction lineage.

---

## 10. Definition of Done & System Acceptance (PRD §26)
A release is accepted only when an end-to-end user journey succeeds in the deployed environment without local setup:
1. **Authentication**: Admin and Engineer login with JWT session issuance and server-enforced RBAC.
2. **Seeded Demo Fleet**: First-run view pre-populated with held-out C-MAPSS FD001 test engines scored deterministically by real model bundles.
3. **Machine Workstation**: Telemetry inspection, rolling anomaly status, calibrated failure probability ($P(\text{Fail} \le H)$), explainability attribution, and transparent lineage (*"How was this prediction generated?"*).
4. **Human Decision Loop**: Alert acknowledge -> maintenance action entry (auto machine status toggle to `maintenance`) -> outcome logging (status restored to `active`).
5. **Data Onboarding**: CSV upload -> column mapping -> validation report.
6. **Compatibility Enforcement**: Compatible data scored successfully; incompatible data (e.g. AI4I) strictly blocked with `409 Conflict (DATASET_INCOMPATIBLE)` and Expected/Found/How-to-fix report.
7. **Model Performance**: Metrics loaded strictly from `model_evaluations`; zero fabricated literals.