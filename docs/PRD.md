# AI Predictive Maintenance System: Product Requirements Document

| | |
|---|---|
| **Version** | 3.0 (final refinement pass of v2.0) |
| **Positioning** | Software-based predictive-maintenance analytics platform; 100% software (no hardware, sensors, IoT devices or live plant connections) |
| **MVP demonstration domain** | NASA C-MAPSS FD001: *simulated turbofan engine degradation* |
| **Primary stack** | Python · FastAPI · scikit-learn / XGBoost or LightGBM · SHAP · PostgreSQL · React · TypeScript · Tailwind · Recharts |
| **Status** | Single source of truth for product requirements |

---

## 0. How to Use This Document (developers and AI IDEs)

**Tier tags.** **[MVP]** = required for the first complete product. **[V2]** = valuable after MVP; do not build during MVP. **[EXP]** = experimental/research; never blocks MVP; adopt only if it demonstrably beats a baseline. Where this document is silent, choose the simpler option.

**Precedence when statements conflict:** §5 (Scope) and §6 (Limitations) → §9 (Functional Requirements) → §13 (Database) → §14 (API) → everything else. The finish line is §26 (MVP Definition of Done).

**Terminology rules (apply to code, UI copy, README and docs):**
- Say **Failure Probability**, **Prediction Reliability**, **Machine Health Indicator**, **recommendation**. Never "confidence" (MVP), "health measurement", or "diagnosis".
- C-MAPSS is **simulated turbofan engine data**. It is never called motor data.
- C-MAPSS sensors are displayed with their **original identifiers** (`sensor_1` … `sensor_21`, `op_setting_1` … `op_setting_3`). No sensor is described as "vibration", "temperature", etc. unless a scientifically justified, cited mapping exists in the adapter (none ships in the MVP).
- Distinguish **AI prediction**, **AI recommendation**, **human action** and **maintenance outcome** everywhere (§FR-14).

**Non-goals for the MVP:** microservices, Kubernetes, message brokers (Celery/Redis/Kafka), WebSockets, multi-tenancy, LLMs in the prediction path, hardware/IoT, live streaming, more than one production dataset adapter, UI-triggered training, UI model activation.

---

## 1. Executive Summary

**Problem.** Industrial equipment fails unexpectedly. Reactive maintenance causes downtime and secondary damage; fixed-interval maintenance wastes effort and still misses failures between inspections.

**Solution.** A **software-based predictive-maintenance analytics platform** that analyzes historical machine sensor data and produces, per machine: an **anomaly assessment**, a **calibrated failure probability** within a stated prediction horizon, a transparent **Machine Health Indicator**, a **traceable explanation** and an **AI-generated maintenance recommendation**. Alerts feed a **human-in-the-loop workflow** in which engineers review, decide, act and record outcomes.

**Positioning (three layers, used consistently throughout):**

| Layer | Statement |
|---|---|
| **Product vision** | A platform that can eventually support industrial rotating and process equipment such as motors, pumps, compressors and turbines. |
| **MVP demonstration domain** | Public datasets for demonstration and model development. Primary: **NASA C-MAPSS FD001 (simulated turbofan engine degradation)**. The MVP has **not** been validated on real industrial machines and must never imply so. |
| **Future industrial domain** | Real motor/pump/compressor datasets onboarded through the dataset adapter / schema-mapping layer, with their own model development and validation. |

**Target users.** Maintenance engineers (primary) and administrators who manage data, models and configuration.

**Portfolio goal.** Demonstrate end-to-end ML engineering: leakage-safe time-series modeling, calibration, explainability, model metadata and lineage, a Model Performance page built from real evaluation artifacts, dataset-compatibility safeguards, a typed REST API, a professional dashboard, and cloud deployment, scoped for one developer.

---

## 2. Problem Statement

- **Reactive maintenance** produces unplanned downtime, secondary damage, expedited repairs and safety exposure.
- **Predictive maintenance (PdM)** estimates when failure becomes likely so maintenance is timely rather than late or wasteful.
- **Why ML:** degradation signatures are multivariate and gradual; fixed alarm limits ignore interactions and drift. Models learn healthy behavior (unsupervised) and failure precursors (supervised), and time-series features capture rate of change.
- **Limits of traditional systems:** static thresholds cause false alarms and missed drift; calendar schedules ignore condition; alerts rarely explain *why*; data is siloed.
- **Data reality:** no public dataset provides motor telemetry with real run-to-failure labels. The product is therefore built around an adapter layer, is honest about each dataset's nature (§8) and treats real-machine support as a future, separately validated step.

---

## 3. Product Vision and Positioning

**Long-term vision.** Onboard a machine dataset through an adapter, verify it is compatible with a versioned model, score it reproducibly, and let engineers act on explained predictions while every prediction stays traceable to its data, mapping and model.

**Principles:** explainable over impressive · recommendations, not verdicts · honest about uncertainty and data limits · replaceable models behind a stable interface · functionality before "AI features".

**Time semantics (maturity path):**

| Stage | Meaning | Tier |
|---|---|---|
| Historical analysis | Score already-collected datasets; "current state" = the latest data point (e.g., "as of cycle 187") | **MVP** |
| Simulated replay | Feed historical data progressively through the pipeline | **V2** |
| Live integration | Real telemetry sources | Future / out of scope |

The UI never implies real-time physical monitoring.

---

## 4. Target Users and Roles

Personas describe the *target product domain*; the MVP demo uses simulated turbofan engines.

| Persona | Needs | MVP role |
|---|---|---|
| **Maintenance engineer** (primary) | Ranked at-risk machines, reasons, recommendation, alert handling, recording actions | Engineer |
| **Plant operator** | Simple status, acknowledging alerts | Engineer |
| **Reliability engineer** | Trends, model performance, thresholds | Engineer (read) / Admin (configure) |
| **Data analyst** | Dataset onboarding, validation, compatibility | Admin |
| **Student/researcher** | Model performance, model cards, lineage | Admin/Engineer |

**Exactly two MVP roles:**

| Capability | Admin | Engineer |
|---|---|---|
| View dashboard, machines, sensors, predictions, explanations, lineage, alerts, datasets and compatibility results, Model Performance, model cards | ✅ | ✅ |
| Acknowledge/resolve alerts; create/update maintenance records | ✅ | ✅ |
| Create/edit/archive machines | ✅ | ❌ |
| Upload/validate/ingest datasets; run compatibility checks; trigger scoring runs | ✅ | ❌ |
| Edit health-indicator config, risk bands, alert rules | ✅ | ❌ (read-only) |
| Reset demo data; view audit log | ✅ | ❌ |
| Register/activate models; create users | CLI only (Admin/maintainer) | ❌ |

A read-only Viewer role, a Users UI, and UI-based model activation are **[V2]**. Authorization is enforced server-side.

---

## 5. Scope Definition

### 5.1 Capability matrix

| Capability | Tier | Notes |
|---|---|---|
| Seeded **Demo Mode** as the first-run experience | MVP | No upload required |
| Authentication (JWT), Admin/Engineer RBAC | MVP | Users created via CLI/seed |
| Fleet dashboard and Machine Details | MVP | |
| Dataset onboarding: upload, **schema mapping**, **validation**, preview | MVP | One production adapter: C-MAPSS FD001 |
| **Dataset Compatibility Check** (blocks inference) | MVP | |
| Anomaly detection: Isolation Forest + statistical baseline | MVP | |
| Failure prediction (binary, horizon **H**, calibrated) | MVP | Logistic → Random Forest → XGBoost **or** LightGBM |
| Machine Health Indicator (deterministic, configurable) | MVP | |
| Explainable predictions (tree SHAP or linear contributions + trend facts) | MVP | |
| Rule-based maintenance recommendations | MVP | Generic rules; no invented physical meanings |
| In-app alerts (high failure probability, severe anomaly, rapid deterioration) | MVP | |
| Human-in-the-loop maintenance action recording | MVP | |
| Model metadata, versions, model cards, lineage ("How was this prediction generated?") | MVP | Registration/activation via CLI |
| **Model Performance page** | MVP | Real evaluation artifacts only |
| Data-quality / reliability warnings (simple, per-input) | MVP | |
| End-to-end deployment | MVP | |
| RUL prediction and charts | V2 | RUL is used *internally* to derive labels only |
| Simulated streaming/replay | V2 | |
| Automated retraining; drift detection (monitoring over time) | V2 | |
| Multiple-model comparison UI; advanced model registry (UI activation, stages, rollback UI) | V2 | |
| Email notifications; low-RUL alerts; maintenance scheduling | V2 | |
| Multi-dataset fleet analytics; fleet health-over-time trend | V2 | |
| Deep learning (MLP/LSTM/GRU); frequency-domain features; One-Class SVM | V2 | |
| Additional adapters (AI4I 2020, Azure PdM, bearing sets); failure-mode classification | V2 | |
| Refresh tokens, password reset, Viewer role, Users UI, recommendation-rule editing | V2 | |
| Job queue/worker, object storage, dedicated inference service | V2 | |
| Transformers; autoencoders / LSTM-autoencoders; conversational AI/NL queries; digital twin; conformal prediction | EXP | Never block MVP; LLMs never in the prediction path |
| Live sensor/IoT integration | Future | Out of scope |

**Boundary clarified:** *reliability warnings* (simple checks on each input window against training reference statistics) are MVP; *drift detection* (monitoring distribution change over time with alerts/retraining triggers) is V2.

---

## 6. Limitations and Responsible Use

This section must appear in the PRD, the README, and an in-app **"About & Responsible Use"** page (shown at first login and linked from the footer).

1. The MVP is a demonstration on public datasets and has **not been validated on real industrial machines**.
2. **C-MAPSS FD001 is simulated turbofan engine degradation data**, not motor, pump or compressor telemetry. **AI4I 2020** is synthetic tabular data. Neither represents real plant conditions.
3. C-MAPSS sensors are shown with their original identifiers; **no physical meaning is asserted** for them in the MVP.
4. Predictions are **statistical estimates**, not guaranteed failure events. Low probability does not guarantee safety; high probability does not confirm a fault.
5. The system is **not a certified industrial safety system** and must not be the sole basis for safety-critical decisions.
6. The system **does not physically diagnose or repair equipment**. Recommendations are decision support; humans decide and act.
7. The **Machine Health Indicator** is a derived product indicator, not a standardized or scientifically validated industrial health measurement.
8. **Prediction Reliability** indicators compare inputs to training data; they do not measure whether a prediction is correct.
9. Real deployment would require representative domain data, new model development and re-validation. Performance may change across machines and operating conditions.
10. Demo content is labelled **"Demo / Simulated Data"**.

### 6.1 README and documentation requirements
The README (and `docs/`) must: (a) state the positioning table from §1; (b) state that the MVP dataset is simulated turbofan data and not validated on real machines; (c) reproduce §6 verbatim; (d) show model metrics **only** as generated by the evaluation script, with dataset, split protocol and date; (e) list demo credentials (Engineer) and the demo-data label; (f) document how to reproduce training and register a model; (g) link the architecture diagram; (h) list V2/EXP items as *not implemented*.

---

## 7. Primary User Journey, Demo Scenario and Upload Workflow

### 7.1 First-run journey [MVP acceptance journey]

```
Login
→ Demo Fleet Dashboard
→ Select Machine
→ View Sensor History
→ View Anomaly Detection
→ View Failure Risk
→ View Explanation
→ View Alert
→ View Maintenance Recommendation
→ Acknowledge Alert
→ Record Maintenance Action
→ Machine status updated → Alert resolved
```

**Acceptance.** *Given* the seeded demo environment and a logged-in Engineer, *when* the Engineer follows this journey using only the UI, *then* each step is reachable without uploading anything; the alert moves `open → acknowledged → resolved`; a maintenance record is stored and linked to the alert; the machine's operational status updates as described in FR-14; and the machine timeline shows the events in order. This journey must pass an automated end-to-end test.

### 7.2 Demo scenario (reproducible)

The seeded fleet (≈8 machines, all simulated C-MAPSS FD001 engines; type "Turbofan engine (simulated)") contains **at least one Healthy, one Warning and one Critical/high-risk machine**. The critical machine demonstrates:

```
Normal behavior
→ Sensor trend changes
→ Anomaly score increases
→ Failure probability increases
→ Machine Health Indicator decreases
→ Alert generated
→ Explanation generated
→ Maintenance recommendation
→ Engineer acknowledges alert
→ Maintenance action recorded
→ Machine status updated
```

**Construction rules (no faked predictions):**
- Demo machines are **held-out FD001 test engines**, never used for training, calibration or threshold selection.
- All predictions, anomaly scores, health indicators, explanations, alerts and recommendations are produced by the **real registered model through the normal scoring pipeline** from a deterministic seeded dataset. Nothing is hand-set.
- A deterministic, documented selection rule in the seed configuration picks engines by *observed pipeline output*: Healthy = final band Healthy/Excellent and low risk; Warning = final band Warning; Critical = early points in Healthy/Excellent bands and final risk ≥ High (or band ≤ Poor). **If a required machine cannot be found, seeding fails loudly; it must not alter data or scores.**
- Only the illustrative human content (a few engineer notes and one pre-completed maintenance example on a different machine) is hand-authored, labelled "Demo / Simulated Data". The critical machine's alert is seeded **open** so the visitor can perform the workflow; "Reset demo data" restores this state.
- The seed also includes two dataset versions to demonstrate onboarding without uploading: the ingested FD001 demo dataset and a **rejected AI4I sample** whose stored compatibility report shows the blocking behavior.
- No metric is hard-coded; the Model Performance page reads the stored evaluation.

### 7.3 CSV onboarding workflow (separate from first run) [MVP, Admin]
```
Upload CSV → Preview → Map columns → Validation report → Compatibility check
→ (blocked with actionable errors) or Ingest → Run inference → Dashboard
```
Repository sample files: a compatible FD001-format CSV, a perturbed FD001-format CSV (to demonstrate compatible-with-warnings and reduced reliability) and an incompatible AI4I-format CSV (verify licences).

---

## 8. Dataset Strategy

> **Verification note.** Dataset facts are stated at a high level from public documentation. Re-verify structure, licence and source in `docs/datasets.md`, and let scripts compute counts and rates instead of hard-coding them.

### 8.1 Primary dataset: NASA C-MAPSS FD001 [MVP]
- **Represents:** *simulated turbofan engine degradation.* Not real telemetry; **not motor data.**
- **Contains:** run-to-failure multivariate time series per engine unit: unit id, cycle, 3 operational settings, 21 sensor measurements (anonymized numeric channels). FD001 is commonly documented as one operating condition and one fault mode. Training units run to failure; test units are truncated before failure with a separate true-RUL file.
- **Adapter canonical fields:** `unit_id`, `cycle`, `op_setting_1..3`, `sensor_1..21`. **UI displays these identifiers unchanged.**
- **MVP uses:** run-to-failure analysis; failure-within-H labels (`RUL ≤ H`, RUL used internally); time-series feature engineering; healthy-baseline anomaly detection; offline RUL experimentation (RUL as a product output is V2).
- **Caveats:** several channels are constant or near-constant in FD001; drop them via empirical feature selection. Raw files are space-delimited without headers, so `prepare_cmapss.py` converts them to CSV with headers.
- **Dashboard label (always visible when this dataset is shown):**
  > **"Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"**

### 8.2 Secondary dataset: AI4I 2020 [V2 in-app; offline exploration allowed]
Synthetic tabular data (10,000 rows): product type, air/process temperature, rotational speed, torque, tool wear, a failure flag and five failure-mode flags. Supports tabular failure prediction, failure-mode classification, SHAP and onboarding demonstrations. **Does not provide** true run-to-failure trajectories, RUL, or a machine-over-time structure. MVP role: offline notebooks to validate that the adapter abstraction is not C-MAPSS-specific, and in-app as the **canonical incompatible upload** (FR-6). An AI4I adapter and failure-mode classification are V2.

### 8.3 Other datasets (reference only) [V2]
Azure PdM sample (simulated telemetry; verify availability/licence), CWRU bearing data (seeded faults, no run-to-failure), NASA/IMS and PRONOSTIA bearing run-to-failure sets. None is needed for the MVP.

### 8.4 Dataset adapter / schema-mapping layer [MVP interface; one adapter]
A code-defined adapter (YAML + small class) declares: `adapter_key` and version; data origin (`simulated`/`synthetic`/`real`); entity/time axis (`cycle` or `timestamp`) and expected sampling; required/optional canonical fields with types, units (if documented) and validity ranges; **sensor metadata** (`id`, `display_id`, and *optional* `physical_meaning` accepted only with a `mapping_source` citation; empty for FD001); default cleaning rules; label-derivation rules (offline only). The mapping UI maps a user's CSV columns onto canonical fields; the saved mapping is part of the dataset version. Real motor/pump/compressor datasets would be added through new adapters, not by editing core code. Nothing outside adapters and prep/seed scripts may hard-code "FD001".

---

## 9. Functional Requirements

Each requirement lists tier, backing pieces (**API §14 · DB §13 · UI §15**) and Given/When/Then criteria.

### FR-1: Authentication and RBAC [MVP]
Email + password login; JWT access token (default 60 min); Argon2id (or bcrypt); roles per §4; users created by CLI/seed; change password; seeded demo Engineer.
*Backed by:* `/auth/*` · `users`, `audit_log` · Login.
- *Given* valid credentials, *when* the user logs in, *then* a token and role are returned and the UI lands on the Demo Fleet Dashboard.
- *Given* an Engineer token, *when* an Admin-only endpoint is called, *then* 403 is returned and the control is not shown.
- *Given* an expired or tampered token, *then* 401 is returned and the UI redirects to login.

### FR-2: Demo Mode (primary first-run experience) [MVP]
The deployed app works immediately after login; no CSV upload is needed to understand the product.
- `seed_demo` creates: demo users, the FD001 demo dataset version (`is_demo = true`, `data_origin = simulated`), machines with sensor history, the registered demo models with model cards and stored evaluations, predictions, anomaly episodes, health indicators, alerts and recommendations generated by the real pipeline, illustrative maintenance records, and the rejected AI4I sample (§7.2).
- Labels: dashboard banner **"Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"**, badge **"Demo / Simulated Data"** on machines, predictions, alerts and maintenance records of demo datasets.
- `POST /admin/demo/reset` restores seeded state and never touches non-demo datasets.
- *Given* an empty database, *when* `seed_demo` runs, *then* a fresh Engineer login shows a populated dashboard containing Healthy, Warning and Critical machines and can complete §7.1.
- *Given* demo alerts were changed, *when* an Admin resets demo data, *then* the seeded state is restored.

### FR-3: Fleet Dashboard and Machine Details [MVP]
**Fleet Dashboard (landing page).** KPI cards: total machines; Healthy/Excellent count; Warning/Poor ("at risk") count; Critical count; average Machine Health Indicator; open alerts. Widgets: health-band distribution; **highest-risk machines** (ranked by failure probability with horizon stated); recent anomaly episodes; recent alerts; failure-probability distribution. Filters: health band, risk level, machine type, location, dataset. Dataset banner and demo badges as in FR-2.

**Machine Details.** Header (machine code, name, type, operational status, dataset badge); summary cards: **Machine Health Indicator** with contribution breakdown, **Failure Probability** with **prediction horizon**, risk level and as-of cycle, **Prediction Reliability**, anomaly status; **sensor history** with selectable original sensor identifiers, zoom, anomaly episodes and abnormal windows shaded; anomaly timeline; **explanation panel**; **AI recommendation card**; **alert and maintenance workflow panel**; prediction history; maintenance history; and a section titled **"How was this prediction generated?"** showing full lineage (FR-16).

- *Given* a seeded fleet, *when* the dashboard loads, *then* KPI counts equal counts derived from each machine's latest prediction.
- *Given* a machine with no predictions, *when* Machine Details loads, *then* an empty state explains scoring has not been run (Admins see a link to run it).
- *Given* any C-MAPSS machine, *then* sensors appear only as `sensor_N`/`op_setting_N`.

### FR-4: Machine Management [MVP]
Admin creates, edits and archives machines (name, unique `machine_code`, type, location, notes, install date, optional dataset version + source unit id). Ingestion can create machines from units using code pattern `<dataset-slug>-v<version>-u<unit>`. **Operational status** (`active`/`maintenance`/`archived`) is human/workflow-driven; **health band** is derived from the latest Machine Health Indicator. Edits are audit-logged; archiving is soft.
- *Given* an existing machine code, *when* an Admin creates another, *then* 409 is returned and the form shows the conflict.
- *Given* an archived machine, *then* it is hidden unless the "Archived" filter is used.

### FR-5: Dataset Onboarding: Upload, Schema Mapping, Validation [MVP]
Admin uploads a CSV (limits per §16), previews it, maps columns to the adapter's canonical fields, and receives a validation report. Nothing is stored in `sensor_readings` until ingestion is confirmed.
- **Validation report:** required columns present after mapping; numeric types; missing values; invalid values (non-numeric, infinite, outside adapter validity ranges); duplicate rows and (unit, time) keys; ordering and gaps; per-unit lengths.
- **Preview:** first/last N rows, per-column statistics, row/unit counts.
- **Cleaning (MVP):** drop exact duplicates; forward-fill within a unit up to a configured gap, marking imputed fields; longer gaps are validation errors. Other strategies are V2.
- **Storage:** raw readings only; scaling and features are computed at inference by the model's stored preprocessing. Every upload is an immutable **dataset version** (SHA-256 checksum) storing its **schema mapping**.
- *Given* a valid supported CSV, *when* the Admin uploads and maps it, *then* the system validates it, shows the report, and allows ingestion only if all required checks pass.
- *Given* malformed rows or missing required columns, *then* the report lists the rule, columns and first N row numbers and ingestion is blocked.
- *Given* an already-ingested checksum, *then* the Admin is warned and must confirm a new version.

### FR-6: Dataset Compatibility Check (blocks inference) [MVP]
Before inference, the system verifies the dataset against the selected model(s) (default: active models). The check is stored, and **re-run server-side at scoring time**. **Incompatible data is never fed to a model; prediction is blocked.**

| # | Check | Failure result |
|---|---|---|
| 1 | Required features present (after mapping) | Error |
| 2 | Feature names/mapping match the model's `input_features`; ordering is enforced by canonical name; duplicate/ambiguous mappings rejected | Error |
| 3 | Data types numeric/parseable | Error |
| 4 | Units match where the model declares them; undeclared units | Error on mismatch; Warning "units unverified" |
| 5 | Expected ranges vs. training reference: fraction outside range | Warning; Error if a feature's median lies outside the training p1–p99 range (probable scale/unit mismatch) |
| 6 | Missing critical values (all model input features are critical unless the model card documents otherwise) | Error above configured maximum; Warning below |
| 7 | Sequence structure: (unit, time) unique and ordered; ≥ minimum window length per unit | Error (structure); Warning per short unit (skipped) |
| 8 | Sampling/cycle information: integer cycle axis present; gaps within tolerance | Error if axis missing; Warning for gaps |
| 9 | Expected feature count equals the model's | Error |
| 10 | **Preprocessing compatibility:** stored preprocessing feature list equals `input_features`; feature-config and preprocessing versions consistent; adapter version supported | Error |
| 11 | **Dataset/model compatibility:** adapter key matches; horizon unit matches the time axis; models active; anomaly and failure models share the same feature-config version | Error |

**Outcome:** `compatible`, `compatible_with_warnings`, `incompatible`. If incompatible the UI shows exactly:

> **"This dataset is not compatible with the selected model."**

then a table for every failed check with **Expected**, **Found** and **How to fix** (actionable, e.g., "Map column `X` to `sensor_3`" or "Upload a file with one row per unit per cycle"). Scoring returns 409 `DATASET_INCOMPATIBLE` unless status is `compatible` or `compatible_with_warnings`. In the MVP only the FD001 adapter is ingestable; other datasets end in `rejected_incompatible`.
- *Given* the AI4I 2020 CSV and an FD001 model, *when* checked, *then* the result is `incompatible` listing missing `unit_id`/`cycle`, missing sensor features, feature-count mismatch and how to fix each.
- *Given* a compatible FD001 CSV with a small fraction of one feature out of range, *then* the result is `compatible_with_warnings` naming the feature and fraction.
- *Given* an incompatible dataset, *when* a scoring run is requested, *then* 409 is returned and no predictions are written.

### FR-7: Inference / Scoring Runs [MVP]
An Admin-triggered **scoring run** (background job) processes a compatible dataset in data order:

```
Machine Data → Validation → Stored Preprocessing → Active Model → Prediction
→ Explanation → Machine Health Indicator → Alert → Dashboard
```

- Features use only past data; points without sufficient history are skipped and recorded, not scored.
- Each scored point persists a prediction row with full lineage; anomaly episodes are updated; alert rules are evaluated **sequentially in data order** (the same behavior V2 replay will have).
- Idempotent: re-running replaces rather than duplicates predictions. Active models are loaded once and cached.
- **No fitting or retraining ever occurs in a scoring run or any request.**
- *Given* a compatible dataset and active models, *when* an Admin starts a run, *then* a job with visible progress is created and each scored point has a prediction with lineage.
- *Given* a job is interrupted and restarted, *then* it completes without duplicate predictions.

### FR-8: Anomaly Detection [MVP]
- **Detector:** Isolation Forest trained on *healthy* windows (definition in the model card; for FD001, early-life cycles of training engines). **Baseline:** transparent statistical detector (rolling/EWMA z-score against healthy statistics). Both are compared during model development; the baseline is retained if Isolation Forest fails to beat it. One-Class SVM is V2; autoencoders are EXP.
- **Outputs per prediction:** `anomaly_score` (higher = more anomalous), `anomaly_severity` ∈ [0,1], `anomaly_flag`. Severity is `clip((q − q_alarm)/(1 − q_alarm), 0, 1)`, where `q` is the fraction of *healthy validation* scores at or below the observed score and `q_alarm` is the alarm quantile calibrated to a target false-positive rate on held-out healthy data (target recorded in the model card).
- **Anomaly episode** (`anomalies`): ≥ M consecutive flagged points (configurable) with start/end `as_of`, peak score, severity level (None/Low/Medium/High via configurable bands), **affected features**, **baseline comparison**, model version and dataset version.
- **Affected features** = features with the largest robust-z deviation from the healthy baseline, shown by original sensor identifier. They are descriptive, not the model's internal attribution and not a fault diagnosis.
- *Given* a healthy segment, *then* few points are flagged and no episode opens at the calibrated target rate (measured value reported on the Model Performance page, never asserted in advance).
- *Given* an episode, *when* opened, *then* start/end, peak severity, affected features, baseline agreement and model version are shown.

### FR-9: Failure Prediction [MVP]
**Prediction target.** *Predict whether a machine/engine will experience a failure within a configurable future prediction horizon **H**.* For C-MAPSS, H is measured in **operating cycles** and "failure" means the end of the simulated run-to-failure trajectory; label = 1 if `RUL ≤ H`.
- **H is a configurable model parameter**, set in the training configuration and fixed for each model version. No H is claimed to be universally correct. The final H is selected during model development from candidate values by evaluating class balance, metric stability and the use case, and recorded with its rationale in the model card. The application reads H from the model version and never hard-codes it.
- **Model selection:** baseline Logistic Regression; candidate Random Forest; primary advanced model XGBoost **or** LightGBM (one, unless comparison adds value). The final model is chosen by *measured* validation performance, preferring the simplest model within a stated tolerance.
- **Requirements:** group-aware splitting (no machine leakage); time-aware evaluation; class-imbalance handling (class weights; resampling only inside training folds); **probability calibration** on a held-out set; **threshold selection** against a stated objective. All recorded in the model card.
- **Prediction output (stored and displayed):**

```
Failure Probability        (calibrated, 0–1)
Prediction Horizon         (H, unit: cycles)
Risk Classification        (Low / Medium / High / Critical; configurable probability bands)
Prediction Timestamp/Cycle (system time + data-time "as of cycle N")
Model Version
```

*Illustrative format only (values not from any real model):*
```
Failure probability: 78%
Prediction horizon: next 20 cycles
Risk: High
```
Default risk bands are starting values: Low < 0.20, Medium 0.20–<0.50, High 0.50–<0.80, Critical ≥ 0.80 (configurable). The UI wording is "estimated probability of failure within the next H cycles"; it is never presented as a guarantee.
- **No "Model Confidence" in MVP.** A confidence figure would appear only with a defensible statistical definition (conformal/bootstrap) [V2/EXP] and its formula shown in a tooltip.
- *Given* a scored point, *then* the display includes probability, horizon (from the model version), risk level, as-of cycle and model version.
- *Given* the final model, *then* its model card records H, H's selection rationale, calibration results, the chosen threshold and its objective.

### FR-10: Machine Health Indicator [MVP]
A **derived product indicator** (0–100, higher = healthier), labelled **"Machine Health Indicator"**. It is not a measured physical property or an industry-standard health measure, and the UI says so.

**Exact formula.**
```
indicator = 100 − Σ_i ( W_i × s_i ),    W_i ≥ 0,  Σ W_i = 100,  s_i ∈ [0,1]
```
| Component | `s_i` definition | MVP default `W_i` (starting values, tunable, not validated) |
|---|---|---|
| Failure Risk | `s_risk` = calibrated failure probability | 50 |
| Anomaly | `s_anom` = `anomaly_severity` (FR-8) | 30 |
| Trend/Degradation | `A` = mean of the top-k (default k = 3) values of \|z_j\|, where z_j is the robust z-score (median/MAD from healthy reference in the model bundle) of the recent-window mean of monitored feature j; `s_trend = clip((A − z_low)/(z_high − z_low), 0, 1)` with configurable `z_low`, `z_high` | 20 |
| Other supported contribution | Reserved slot for additional supported signals (RUL in V2) | 0 (not enabled) |

The indicator is rounded to an integer; bands use the rounded value. Default bands (configurable, contiguous, covering 0–100): 0–30 Critical · 31–50 Poor · 51–70 Warning · 71–85 Healthy · 86–100 Excellent.
**Stored** per prediction: `health_indicator`, `health_components` (each `s_i` and penalty points) and `health_config_id`.
**UI example:**
```
Machine Health Indicator: 64/100   (derived indicator)
Failure Risk Contribution            −18
Anomaly Contribution                 −10
Trend/Degradation Contribution        −8
Other Supported Contribution         not enabled
Overall: Warning
```
- *Given* stored components and config, *when* recomputed, *then* the result is identical (unit-tested).
- *Given* an Admin edits weights or bands, *when* saved, *then* a new config version applies only to future scoring runs and past predictions keep their `health_config_id`.

### FR-11: Explainable Predictions [MVP]
1. **Local feature contributions:** tree models → SHAP `TreeExplainer`; linear model → coefficient × standardized value. They explain the model's **raw (pre-calibration) risk score**; the calibrated probability is a monotone transform (UI: "contributions to the model's risk score"). Other model types cannot be registered in MVP.
2. **Sensor trend facts:** percent change over the last N cycles, slope, and position relative to the healthy baseline band, per original sensor identifier.
3. **Global importance:** stored with the evaluation and shown on the Model Performance page.

Explanations are computed on first request and cached in `predictions.explanation`; scoring precomputes them for alert-triggering predictions and each machine's latest prediction. A template engine (no LLM) produces text in this form: *"Failure probability is `<P>` within the next `<H>` cycles mainly because `<sensor_id>` changed by `<x>%` over the last `<N>` cycles and `<sensor_id>` is outside its healthy range."* Every sentence traces to stored numbers; if contributions and trend facts disagree, both are shown.
**UI:** headline; top 5–8 contribution bars (red raises, blue lowers); small sensor charts with the abnormal window shaded; "How was this prediction generated?" link; persistent decision-support disclaimer.
- *Given* a high-risk prediction, *then* the headline names ≥ 2 contributing features by original identifier with numeric evidence.
- *Given* the deployed model is Logistic Regression, *then* linear contributions are shown and no tree explainer is invoked.

### FR-12: AI Maintenance Recommendations [MVP]
Rule-based mapping from (risk level, anomaly severity level, health band, trend severity, top contributing feature identifiers, reliability status) to a recommendation (text, priority, rationale, rule id). Rules ship as versioned YAML and are read-only in the UI. MVP recommendations are **deliberately generic** and make no claims about physical components, e.g.: *"Schedule an inspection of this unit and review the flagged sensors: `<ids>`"*, *"Increase monitoring frequency and review recent operating settings"*, *"Continue monitoring"*. Domain-specific recommendations (e.g., naming components) are allowed only for adapters with a cited, validated sensor mapping [V2].
Every recommendation is labelled **"AI-generated recommendation, not a confirmed diagnosis. Verify with a qualified engineer."** A snapshot is stored on the alert and latest prediction.
- *Given* an alert, *then* its recommendation, disclaimer and rule id are shown.

### FR-13: Alerts [MVP: in-app]
| Type | Default trigger (Admin-configurable) |
|---|---|
| `high_failure_risk` | failure probability ≥ `alert_threshold` for N consecutive points (default = the model's decision threshold at activation; overridable) |
| `severe_anomaly` | anomaly episode with severity level ≥ configured level |
| `rapid_deterioration` | Machine Health Indicator drops ≥ X points within Y data points |

Low-RUL alerts and email are [V2]. One open alert per (machine, type). Alerts store data-time `as_of`, system `triggered_at`, triggering prediction, reliability flag and recommendation snapshot. Status: `open → acknowledged → resolved` (FR-14). No cooldown logic (datasets are static in MVP).
- *Given* probabilities above threshold for N consecutive points, *then* exactly one open `high_failure_risk` alert exists for the machine.
- *Given* the triggering prediction has reduced reliability, *then* the alert is flagged "reduced reliability".

### FR-14: Human-in-the-Loop Maintenance Workflow [MVP]
The system keeps four things distinct, in data and UI:

| Concept | Meaning | Stored as | UI label |
|---|---|---|---|
| **AI prediction** | What the model estimates | `predictions` | "AI prediction" |
| **AI recommendation** | What the system suggests an engineer consider | snapshot on `alerts` / `predictions.recommendation`; copied into the record as `recommended_action` | "AI recommendation (not a diagnosis)" |
| **Human decision & action** | What the engineer decides and does | `maintenance_records.decision`, `decision_rationale`, `action_taken`, engineer, timestamps | "Engineer decision" |
| **Maintenance outcome** | Whether the issue was resolved | `maintenance_records.outcome`, alert `resolution` | "Outcome" |

```
AI Prediction → Alert → Human Review (acknowledge) → Recommendation
→ Human Decision → Maintenance Action → Outcome
```

- **Alert:** `open → acknowledged → resolved`. Resolving requires a linked record with status `completed`, or a resolution reason `false_alarm` / `no_action_needed` with a note.
- **Maintenance record:** machine; related alert; issue; recommended action (AI, read-only copy); **decision** (`followed_recommendation`/`modified`/`declined`) with rationale; action taken; engineer; timestamps; status (`recommended`, `in_progress`, `completed`, `cancelled`); outcome (`resolved`, `unresolved`, `no_issue_found`); notes. An `unresolved` outcome keeps the alert `acknowledged` and prompts a follow-up.
- **Machine status update (workflow side effect):** a record `in_progress` sets the machine's operational status to `maintenance`; a `completed` record with outcome `resolved` or `no_issue_found` returns it to `active`. This changes *operational status only*; the Health Indicator and failure probability are data-derived and change only when new data is scored. Changes are audit-logged.
- The system never claims the AI diagnosed or repaired equipment. Using outcomes to tune thresholds/retrain is [V2].
- *Given* an open alert, *when* an engineer acknowledges with a note, *then* status becomes `acknowledged` with user and timestamp.
- *Given* an acknowledged alert, *when* the engineer records an in-progress inspection, *then* the machine status becomes `maintenance`; *when* it is completed with outcome `resolved` and the alert is resolved, *then* status returns to `active`, the record links to the alert and the timeline shows both events.
- *Given* an acknowledged alert with no completed record, *when* the engineer resolves without a valid reason, *then* the API returns 422.

### FR-15: Data Quality and Reliability Warnings [MVP]
Before/at prediction, the pipeline compares the input window with the model's stored training reference statistics and computes: fraction of features outside expected ranges; required values missing/imputed in the window; **stale/gapped recent data** (missing recent cycles or timestamps within the window; age-of-last-reading staleness applies only to V2 replay/live); maximum robust-z shift of window means vs. training reference (a practical distribution-difference check); windows too short (not scored). Structural incompatibility is handled earlier and blocks inference (FR-6).
`reliability_status` = `ok` | `reduced` with `reliability_flags` listing tripped indicators (thresholds in read-only settings). When `reduced`, the prediction, indicator and any alert show:

> **"Prediction reliability may be reduced because the input data differs from the model's training data."**

with the specific reasons. The UI never claims the model knows a prediction is correct; drift monitoring over time is V2.
- *Given* a window with more out-of-range features than the tolerance, *then* `reduced` is stored and the warning and reasons appear.

### FR-16: Model Metadata, Versioning and Lineage [MVP]
**Offline training is separate from the app.** Training and evaluation run through the `ml/` CLI and produce a **model bundle** (stored preprocessing/scaler, feature-transformation reference, trained model, calibrator, decision threshold, `input_features`, healthy reference statistics, explainer configuration, checksum manifest), a **model card** and an **evaluation record**. A backend CLI (`register-model`, `activate-model`) registers/activates it. The application never trains during a request. UI activation, model comparison and rollback UI are V2.
- **Status:** `registered → active → retired`. Rules: activation requires a complete model card **and** an attached evaluation record (CLI/service validation plus DB CHECK on card completeness); at most one active model per (adapter, task); active anomaly and failure models share `feature_config_version`; activation is audit-logged.
- **Prediction lineage.** Every prediction traces to:
```
Machine → Dataset → Dataset Version → Schema Mapping → Feature Configuration
→ Preprocessing Version → Model Version → Prediction Horizon → Prediction Timestamp/Cycle
```
stored as: machine, dataset version (name + version), `schema_mapping_hash`, `feature_config_version`, `preprocessing_version`, failure and anomaly model version ids/types, `horizon`/`horizon_unit`, `predicted_at`, `as_of_index`, `input_window`, `health_config_id`.
- The Machine Details section **"How was this prediction generated?"** displays this lineage and links to the model card and Model Performance page.
- *Given* an activation attempt for a model without a complete card or evaluation, *then* it fails with `MODEL_CARD_INCOMPLETE` listing what is missing.
- *Given* any stored prediction, *when* the engineer opens "How was this prediction generated?", *then* every lineage field above is shown.

### FR-17: Model Performance Page [MVP]
A dedicated **Model Performance** page shows, for every **active** model (and read-only history for retired/registered versions), only stored evaluation artifacts produced by the evaluation script. **No metric is hard-coded, typed by hand, or fabricated.**
- **Classification metrics (failure model):** Precision, Recall, F1, ROC-AUC, PR-AUC, calibration metric (Brier score and/or expected calibration error), all at the model's documented threshold where applicable.
- **Visualizations:** confusion matrix; ROC curve; precision–recall curve; calibration plot; feature importance.
- **Anomaly model:** precision/recall/F1/false-positive rate under the stated **proxy labels**, with comparison to the statistical baseline (proxy clearly labelled).
- **Model information:** model type, model version, dataset, dataset version, feature set, prediction horizon, training date, evaluation date, evaluation methodology (split protocol, test set description).
- **Limitations:** known limitations from the model card (including "simulated turbofan data; not validated on real machines").
- **Empty state:** if no model has been trained/registered or a section's evaluation is missing, show **"Model evaluation not available."**
- *Given* an active model with a stored evaluation, *then* every metric and chart is rendered from that record and its evaluation date is shown.
- *Given* no registered model, *then* the page shows "Model evaluation not available." and no numbers.

### FR-18: Configuration [MVP]
Admin-editable: Machine Health Indicator config (weights, bands, trend parameters; new version per change), risk bands, alert rules. Reliability thresholds and anomaly severity bands are seeded and read-only in the UI (editing V2). Recommendation rules are read-only. Changes are audit-logged and visible to Admin.

---

## 10. System Architecture

```
┌──────────────────┐  HTTPS/JSON+JWT  ┌────────────────────────────────────────────┐
│ React frontend   │ ───────────────▶ │ FastAPI backend (single deployable)        │
│ (Vercel)         │ ◀─────────────── │  routers → services → repositories         │
└──────────────────┘                  │  ┌───────────────┐   ┌──────────────────┐  │
                                      │  │ Adapter layer │   │ ML runtime       │  │
                                      │  │ (mapping,     │   │ (bundle loader,  │  │
                                      │  │ compat checks)│   │ predictor iface, │  │
                                      │  └───────────────┘   │ explainer)       │  │
                                      │  ┌───────────────┐   └──────────────────┘  │
                                      │  │ Alert &       │   ┌──────────────────┐  │
                                      │  │ workflow svc  │   │ DB-backed jobs   │  │
                                      │  └───────────────┘   └──────────────────┘  │
                                      └───────────────┬────────────────────────────┘
                                                      │ SQLAlchemy
                                             ┌────────▼────────┐
                                             │ PostgreSQL      │
                                             └─────────────────┘
  Offline (developer machine / CI): ml/ pipeline → bundle + model card + evaluation → register-model / activate-model CLI
```

### 10.1 Training (offline, never in a request)
```
Dataset → Validation → Preprocessing → Feature Engineering → Training → Evaluation → Model Registration
```
### 10.2 Inference (application)
```
Machine Data → Validation → Stored Preprocessing → Active Model → Prediction
→ Explanation → Health Indicator → Alert → Dashboard
```
The same feature-transformation package (`ml/src/features`) is imported by training and the backend to prevent training/serving skew. **The application never retrains automatically.**

### 10.3 Components
- **Frontend ↔ backend:** REST, JSON, Bearer JWT, types generated from OpenAPI.
- **Backend ↔ PostgreSQL:** SQLAlchemy 2.x, Alembic, pooling.
- **Backend ↔ ML runtime:** in-process behind a stable interface so models are replaceable:
  `ModelPredictor: predict(features) → probability|score · explain(features) → Explanation · metadata`.
- **Jobs:** ingestion and scoring as DB-backed jobs run by background tasks on a single instance; idempotent and resumable. Celery/Redis is V2.
- **Alert/workflow service:** invoked by scoring; applies `alert_rules`; updates machine operational status from maintenance records.
- **Model artifacts:** files under `MODEL_ARTIFACT_DIR` shipped with the image; checksum verified at load.

---

## 11. Machine Learning Methodology

### 11.1 Pipeline
`Raw dataset → Validation → Cleaning → Missing values → Feature engineering → Scaling → Split → Training → Hyperparameter optimization → Evaluation → Model selection → Calibration/threshold selection → Bundle → Model card + evaluation record → Registration`

### 11.2 Horizon selection and splits (FD001)
- **Choosing H:** evaluate a small set of candidate horizons (in cycles); compare resulting class balance, metric stability across folds and the use-case trade-off (earlier warning vs. more positives); choose one, and document the choice and its limits. H is a training-configuration parameter stored on the model version.
- **Splits:** official FD001 *training* engines split **by engine** into train and validation (calibration + threshold selection) partitions; hyperparameter search via **GroupKFold** on the train partition. Final evaluation uses the official FD001 *test* engines (per-cycle RUL derived from the provided final RUL); used once. Demo machines come from test engines only. With ~100 training engines, report variability across folds and note it as a limitation.

### 11.3 Data-leakage prevention (mandatory)
1. No engine in more than one split. 2. Past-only features (no centered windows). 3. Scalers, imputers, thresholds, calibrators and reference stats fit on training/designated partitions only. 4. Outcome-encoding columns (`rul`, failure flags, post-failure rows) never model inputs. 5. Feature selection inside CV folds; resampling only inside training folds. 6. Automated tests assert split disjointness and `feature time ≤ as_of`.

### 11.4 Feature engineering (`feature_config.yaml`, versioned)
| Family | Examples |
|---|---|
| Rolling statistics | mean, std, min, max, median, range |
| Moving averages | SMA, EWMA at multiple spans |
| Rate of change | first difference, window slope |
| Baseline deviation | robust z vs. healthy baseline, % change vs. earlier window |
| Cross-sensor | rolling correlations, ratios (only where meaningful; no physical claims) |
| Operating context | cycle count, operational settings |
| Statistical | skewness, kurtosis, RMS, peak-to-peak |
| Missingness | imputed fraction in window |
| Frequency-domain | **[V2]** only for datasets with raw high-rate signals |

### 11.5 Evaluation
Accuracy alone is inappropriate for imbalanced failure data. Report for the failure model: precision, recall, F1, ROC-AUC, **PR-AUC (primary)**, confusion matrix at the chosen threshold, calibration curve and Brier/ECE, feature importance, and event-level results (failing engines warned ≥ k cycles ahead; false alarms per engine). Anomaly detection: precision, recall, F1, FPR on healthy held-out data, lead time, comparison with the statistical baseline, using **proxy labels** (points with `RUL ≤ H` = degraded; high-RUL points = healthy), stated as a proxy. RUL metrics (MAE, RMSE, R²) are [V2]. All artifacts feed the Model Performance page; no number is quoted anywhere until produced by the reproducible evaluation script.

### 11.6 Model selection
A model is adopted only if it beats the trivial baseline and Logistic Regression on PR-AUC (or the statistical baseline for anomalies); ties favor simpler/more interpretable models. Deep learning is V2 and adopted only if it clearly and consistently beats the tabular winner; Transformers/autoencoders are EXP.

---

## 12. Model Card Template (required for activation)

`docs/model_cards/<name>_<version>.md`, mirrored in `model_versions.model_card`. Required: **Model name · Version · Task · Dataset · Dataset version · Training date · Evaluation date · Feature set · Target definition · Prediction horizon (and selection rationale) · Training methodology · Evaluation methodology · Metrics (reference to the evaluation record and commit) · Known limitations · Intended use · Out-of-scope use · Calibration information · Responsible-use disclaimer.**

---

## 13. Database Design (PostgreSQL)

UUID primary keys (`BIGSERIAL` for `sensor_readings`, `predictions`); `created_at/updated_at` timestamptz; explicit `ON DELETE`; Alembic migrations. **Data time** (`as_of_index`, cycle/timestamp) is distinct from **system time** (`predicted_at`, `triggered_at`, `created_at`).

| Table | Key fields | Constraints / indexes / purpose |
|---|---|---|
| **users** | id, email, password_hash, full_name, role (`admin`/`engineer`), is_active, last_login_at | unique(email). Auth/RBAC |
| **datasets** (each row = immutable dataset **version**) | id, name, version, adapter_key, adapter_version, data_origin (`simulated`/`synthetic`/`real`), is_demo, checksum_sha256, status (`uploaded`/`validated`/`ingested`/`rejected_incompatible`), column_mapping JSONB (the **schema mapping**), schema_mapping_hash, validation_report JSONB, row_count, unit_count, uploaded_by | unique(name, version); index(status). Dataset onboarding, lineage |
| **dataset_compatibility_checks** | id, dataset_id, failure_model_version_id, anomaly_model_version_id, status, report JSONB (per check: rule, severity, expected, found, how_to_fix), checked_at, checked_by | index(dataset_id, checked_at DESC). FR-6 UI and blocking |
| **machines** | id, machine_code, name, machine_type, location, notes, install_date, operational_status (`active`/`maintenance`/`archived`), dataset_id (nullable), source_unit_id, created_by | unique(machine_code); index(operational_status); index(dataset_id) |
| **sensor_readings** | id, machine_id, dataset_id, cycle_index (and/or recorded_at), values JSONB (canonical keys e.g. `sensor_1`), imputed JSONB | **unique(machine_id, dataset_id, cycle_index)**; index(machine_id, cycle_index). Sensor history |
| **model_versions** | id, name, task (`anomaly`/`failure_risk`), model_type, version, adapter_key, status (`registered`/`active`/`retired`), artifact_uri, artifact_sha256, input_features JSONB, feature_config_version, preprocessing_version, horizon, horizon_unit (null for anomaly), decision_threshold, training_dataset_id, training_date, git_commit, model_card JSONB, model_card_complete bool, activated_at | **partial unique** (adapter_key, task) WHERE status='active'; **CHECK** (status<>'active' OR model_card_complete). Metadata, lineage |
| **model_evaluations** | id, model_version_id, evaluation_run_id, evaluated_at, evaluation_dataset_id, methodology JSONB, metrics JSONB, curves JSONB (ROC, PR, calibration bins, confusion matrix), feature_importance JSONB, limitations JSONB | unique(model_version_id, evaluation_run_id). Feeds Model Performance page only |
| **predictions** | id, machine_id, dataset_id, schema_mapping_hash, failure_model_version_id, anomaly_model_version_id, health_config_id, feature_config_version, preprocessing_version, **horizon, horizon_unit**, as_of_index, predicted_at, input_window JSONB (unit, first/last cycle, length, input hash), **failure_probability, risk_level**, decision_threshold_exceeded, anomaly_score, anomaly_severity, anomaly_flag, **health_indicator**, health_components JSONB, reliability_status (`ok`/`reduced`), reliability_flags JSONB, recommendation JSONB, explanation JSONB (cached) | unique(machine_id, dataset_id, as_of_index, failure_model_version_id, anomaly_model_version_id); index(machine_id, as_of_index DESC); index(risk_level) |
| **anomalies** (episodes) | id, machine_id, dataset_id, anomaly_model_version_id, start_as_of, end_as_of, is_ongoing, peak_score, peak_severity_level, affected_features JSONB, baseline_comparison JSONB, first_prediction_id | index(machine_id, start_as_of DESC); index(peak_severity_level) |
| **alerts** | id, machine_id, prediction_id, alert_type, severity, message, as_of_index, triggered_at, reliability_flag, recommendation JSONB, status (`open`/`acknowledged`/`resolved`), acknowledged_by/at/note, resolved_by/at, resolution (`issue_resolved`/`false_alarm`/`no_action_needed`), resolution_note | **partial unique** (machine_id, alert_type) WHERE status<>'resolved'; index(status, severity, triggered_at DESC) |
| **maintenance_records** | id, machine_id, alert_id (nullable), issue, recommended_action (AI copy), decision (`followed_recommendation`/`modified`/`declined`), decision_rationale, action_taken, performed_by, performed_at, status (`recommended`/`in_progress`/`completed`/`cancelled`), outcome (`resolved`/`unresolved`/`no_issue_found`), notes | index(machine_id, performed_at DESC); index(alert_id) |
| **health_indicator_configs** | id, version, weights JSONB, bands JSONB, trend_params JSONB, is_active, created_by | one active (partial unique) |
| **alert_rules** | id, alert_type, params JSONB, enabled | unique(alert_type) |
| **settings** | key, value JSONB, updated_by | keys: `risk_bands`, `reliability_thresholds`, `anomaly_severity_bands` |
| **jobs** | id, type (`ingest`/`scoring`/`demo_reset`), status, progress, params JSONB, result JSONB, error, created_by | index(status, created_at). Progress UI |
| **audit_log** | id, user_id, action, entity_type, entity_id, before JSONB, after JSONB, created_at | index(entity_type, entity_id). Admin accountability (Settings tab) |

**Reserved for V2 (do not create):** RUL columns, `refresh_tokens`, failure-mode fields, `recommendation_rules` table (rules are YAML), replay/streaming tables, drift-monitoring tables.

**Output ↔ storage audit:** failure probability/horizon/risk/model version/as-of → `predictions`; anomaly outputs → `predictions` + `anomalies`; health indicator components → `predictions.health_components`; reliability → `predictions`; explanation → `predictions.explanation`; recommendation → `predictions`/`alerts`; human decision/action/outcome → `maintenance_records` + `alerts`; evaluation → `model_evaluations`; compatibility → `dataset_compatibility_checks`.

---

## 14. API Design

Base `/api/v1`, JSON, Bearer JWT unless noted. Pagination `?page=&page_size=` (max 100). Error body `{"error":{"code","message","details"}}`. **Common errors:** 401, 403, 404, 409, 413, 422, 429, 500 (no stack traces).

### 14.1 Auth (FR-1)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| POST | `/auth/login` | `{email,password}` → `{access_token, expires_in, user}` | None | 401; 429 |
| GET | `/auth/me` | → `{id,email,role}` | Any | 401 |
| POST | `/auth/change-password` | `{current,new}` → 204 | Any | 401 wrong current; 422 weak |

### 14.2 Machines (FR-3, FR-4)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| GET | `/machines` | filters `operational_status, health_band, risk_level, location, dataset_id, q` → list with latest indicator/probability/horizon | Any | |
| POST | `/machines` | `{machine_code,name,machine_type,location,notes,install_date,dataset_id?,source_unit_id?}` → 201 | Admin | 409 duplicate; 404 |
| GET | `/machines/{id}` | → machine + latest prediction summary + dataset badge info | Any | 404 |
| PATCH | `/machines/{id}` | partial → machine | Admin | 404; 409; 422 |
| POST | `/machines/{id}/archive` | → 200 | Admin | 404; 409 open alerts without `force` |
| GET | `/machines/{id}/timeline` | `from,to` → merged anomalies, alerts, maintenance events | Any | 404 |
| GET | `/machines/{id}/sensors` | `from,to,sensors[],max_points` → `{index[], series{sensor_id:[…]}, imputed_marks}` | Any | 404; 422 unknown sensor |

### 14.3 Datasets, Compatibility, Jobs (FR-5, FR-6)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| POST | `/datasets` | multipart CSV + `name` → 201 `{id, version, status:'uploaded', preview, detected_columns}` | Admin | 400; 413; 415; 422 |
| POST | `/datasets/{id}/validate` | `{adapter_key, column_mapping, cleaning_options}` → validation report | Admin | 404; 410 `STAGING_EXPIRED`; 422 mapping incomplete |
| POST | `/datasets/{id}/compatibility-check` | `{failure_model_version_id?, anomaly_model_version_id?}` → `{status, checks[{rule,severity,expected,found,how_to_fix}]}` | Admin | 404; 409 not validated; 409 no active model |
| GET | `/datasets` · `/datasets/{id}` · `/datasets/{id}/compatibility` | list · detail · latest check | Any | 404 |
| POST | `/datasets/{id}/ingest` | `{create_machines, confirm:true}` → 202 `{job_id}` | Admin | 409 already ingested/rejected; 422 validation failed |
| GET | `/jobs/{id}` | → `{status, progress, result, error}` | Admin | 404 |

### 14.4 Inference, Predictions, Explanations, Anomalies (FR-7–FR-11, FR-15, FR-16)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| POST | `/scoring-runs` | `{dataset_id, machine_ids?}` → 202 `{job_id}` | Admin | 404; 409 `DATASET_INCOMPATIBLE`; 409 no active models |
| GET | `/machines/{id}/predictions` | `from,to,page` → history | Any | 404 |
| GET | `/machines/{id}/predictions/latest` | → latest prediction | Any | 404; 404 `NOT_SCORED` |
| GET | `/predictions/{id}` | → prediction with **lineage** object, health components, reliability | Any | 404 |
| GET | `/predictions/{id}/explanation` | → `{headline, contributions[], trend_facts[], text, computed_at}` | Any | 404; 409 explainer unavailable |
| GET | `/anomalies` · `/machines/{id}/anomalies` | filters → episodes | Any | 404; 422 |

### 14.5 Models and Model Performance (FR-16, FR-17)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| GET | `/models` | filters `task,status` → list with metadata (type, version, dataset, horizon, dates) | Any | |
| GET | `/models/{id}` · `/models/{id}/card` | detail · model card | Any | 404 |
| GET | `/models/{id}/evaluation` | → metrics, curves, feature importance, methodology, limitations | Any | 404 `EVALUATION_NOT_AVAILABLE` (UI shows "Model evaluation not available.") |

*(Registration, activation and retirement are CLI operations in MVP.)*

### 14.6 Alerts and Maintenance (FR-12–FR-14)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| GET | `/alerts` · `/alerts/{id}` | filters `status,severity,type,machine_id` → list · detail (recommendation snapshot) | Any | 404 |
| POST | `/alerts/{id}/acknowledge` | `{note?}` → alert | Admin/Engineer | 404; 409 not open |
| POST | `/alerts/{id}/resolve` | `{resolution, note}` → alert | Admin/Engineer | 404; 409 not acknowledged; 422 no completed record and no valid reason |
| GET | `/machines/{id}/maintenance` | → records | Any | 404 |
| POST | `/maintenance` | `{machine_id, alert_id?, issue, decision, decision_rationale, action_taken, status, outcome?, notes}` → 201 (updates machine operational status per FR-14) | Admin/Engineer | 404; 422 |
| PATCH | `/maintenance/{id}` | partial → record | Admin/Engineer | 404; 409 cancelled |

### 14.7 Dashboard (FR-3)
| Method | Endpoint | Response | Auth |
|---|---|---|---|
| GET | `/dashboard/summary` | totals, band counts, average indicator, open alerts, dataset label info | Any |
| GET | `/dashboard/priority-machines?limit=` | ranked by failure probability (with horizon) | Any |
| GET | `/dashboard/recent-anomalies?limit=` · `/dashboard/recent-alerts?limit=` | latest items | Any |
| GET | `/dashboard/probability-distribution` | histogram bins | Any |

### 14.7 Settings and Admin (FR-2, FR-18)
| Method | Endpoint | Request → Response | Auth | Errors |
|---|---|---|---|---|
| GET/PUT | `/settings/health-indicator` | config · new version | Read: Any · Write: Admin | 422 bands not contiguous 0–100; weights ≠ 100 |
| GET/PUT | `/settings/risk-bands` · `/settings/alert-rules` | values | Read: Any · Write: Admin | 422 |
| GET | `/settings/reliability` · `/settings/recommendation-rules` | read-only | Any | |
| POST | `/admin/demo/reset` | → 202 `{job_id}` | Admin | 409 demo not seeded |
| GET | `/admin/audit-log` | paginated | Admin | |
| GET | `/health` | `{status, db, models_loaded}` | None | |

**Deferred (V2):** RUL, replay/streaming, email, adapter admin, training/activation endpoints, users endpoints, refresh tokens.

---

## 15. Frontend Requirements

**Stack:** React 18 + TypeScript, Vite, Tailwind CSS, Recharts, React Router, TanStack Query, React Hook Form + Zod, OpenAPI-generated types.

**Pages (MVP):** Login · **Demo Fleet Dashboard (default landing)** · Machines · Machine Details · Alerts (list + detail) · Datasets (list, upload wizard [Admin], validation and compatibility results [all]) · **Model Performance** · Settings (health indicator, risk bands, alert rules; read-only reliability/recommendation rules; audit-log tab for Admin) · About & Responsible Use.

**Model Performance layout:** active-model selector (failure model, anomaly model) → metric cards (Precision, Recall, F1, ROC-AUC, PR-AUC, Brier/ECE) → charts (confusion matrix, ROC, PR, calibration plot, feature importance) → model information table → limitations panel → evaluation methodology. Missing data → "Model evaluation not available."

**Upload wizard:** ① Upload & preview → ② Map columns → ③ Validation report → ④ Compatibility check (exact incompatibility message and Expected/Found/How-to-fix table) → ⑤ Confirm & ingest (job progress) → ⑥ Run inference.

**Navigation:** left sidebar (Dashboard, Machines, Alerts, Datasets, Model Performance, Settings, About); top bar with alert bell, user menu, and a persistent **dataset banner** ("Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data" plus "Demo / Simulated Data" badge). From the dashboard an elevated-risk machine opens in ≤ 1 click.

**Key components:** `KpiCard`, `HealthIndicatorGauge` + `ContributionBreakdown`, `RiskBadge`, `ReliabilityBadge`, `SensorChart` (original identifiers, anomaly shading, imputed marks), `ProbabilityChart`, `ExplanationPanel`, `AnomalyTimeline`, `AiRecommendationCard`, `WorkflowPanel` (AI prediction · AI recommendation · Engineer decision · Outcome), `MaintenanceForm`, `LineageSection` ("How was this prediction generated?"), `CompatibilityReport`, `ModelMetricCard`, `ConfusionMatrix`, `RocChart`, `PrChart`, `CalibrationPlot`, `FeatureImportanceChart`, `DataTable`, `DatasetBanner`, `ConfirmDialog`, `Toast`.

**States on every data component:** loading (skeletons), empty (explanation + action), error (message, retry, request id), unsupported/partial.

**UI copy rules:** "Failure Probability" with horizon; "Prediction Reliability"; "Machine Health Indicator (derived)"; "AI recommendation"; original sensor identifiers; data time as "cycle N", never "live".

**Responsive & accessibility:** desktop-first; sidebar collapses on tablet; mobile single column with card tables; WCAG AA; status by icon + text; chart data-table fallback. **Look:** professional industrial analytics SaaS: neutral slate palette, dark mode, semantic colors reserved for status, tabular numerals.

---

## 16. Security Requirements

| Area | Requirement |
|---|---|
| Authentication | Short-lived JWT (default 60 min), pinned algorithm, secret from env, login backoff; no refresh tokens in MVP |
| Passwords | Argon2id (or bcrypt); minimum length; hashes never returned/logged |
| Authorization | Server-side role checks on every route; deny by default; audit log for admin actions |
| Input validation | Pydantic strict schemas; ORM/parameterized queries; output encoding |
| File uploads | Extension + content-type + content sniffing; `MAX_UPLOAD_MB`, row/column/cell limits; streamed parsing with timeouts; UTF-8 enforced; random filenames outside web root; no archives; content never executed |
| Malicious CSV | Neutralize cells starting with `= + - @ \t \r` on export/display; strict numeric parsing; reject NaN/Inf where invalid |
| Rate limiting | Per-IP/user (in-memory limiter suffices for one instance); stricter on login, upload, scoring |
| Secrets/config | Env vars only; `.env.example` committed; nothing secret in the frontend bundle |
| CORS/transport | Explicit origin allow-list; HTTPS, HSTS, security headers |
| Database | Least-privilege app role; TLS; separate migration role; backups |
| Model artifacts | Load only registered artifacts from `MODEL_ARTIFACT_DIR`; verify SHA-256; never deserialize user-supplied model files |
| Demo safety | Demo Engineer cannot upload, change settings/users, or reset demo; reset touches demo data only |
| Dependencies | Pinned; `pip-audit`, `npm audit`, secret scanning in CI |

---

## 17. Deployment Architecture

| Layer | Recommendation |
|---|---|
| Frontend | Vercel (Vite static build); `VITE_API_BASE_URL` |
| Backend | Render or Railway Docker web service, single instance; health check `/api/v1/health`; document free-tier cold starts |
| Database | Managed PostgreSQL (Neon, Supabase or platform Postgres) with TLS and backups |
| ML | In-process runtime; bundle files in the image; **training runs offline/local or in CI, never on the web instance** |
| Jobs | DB-backed jobs + background tasks (queue is V2) |
| Upload staging | Ephemeral local disk; if lost, `STAGING_EXPIRED` and re-upload; ingested data lives in Postgres |
| CI/CD | GitHub Actions: lint → type-check → tests → build → deploy; migrations as a release step; `seed_demo` run as a release/one-off step |

**Backend env vars:** `DATABASE_URL`, `JWT_SECRET`, `JWT_ALGORITHM`, `ACCESS_TOKEN_TTL_MIN`, `CORS_ORIGINS`, `MODEL_ARTIFACT_DIR`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `MAX_ROWS`, `RATE_LIMIT_*`, `ENVIRONMENT`, `LOG_LEVEL`, `DEMO_MODE_ENABLED`, `SENTRY_DSN` (optional). **Frontend:** `VITE_API_BASE_URL`. **Production:** debug off; API docs gated; models loaded once at startup with a warm-up; structured logs; first admin via `seed_admin`.

---

## 18. Non-Functional Requirements

*Initial targets; revisit after measurement. No values are claimed.*

| Category | Requirement |
|---|---|
| API response time | Read endpoints p95 `[TBD; initial goal < 500 ms]` |
| Inference latency | Single-point inference p95 `[TBD]`; scoring runs asynchronous with progress; first explanation shows a loading state |
| Frontend | Interactive dashboard `[TBD; initial goal < 3 s]`; charts limited to a few thousand server-downsampled points |
| Scalability | Tens–hundreds of machines, up to low millions of readings via indexes/downsampling; not for high-frequency streams |
| Availability | Best-effort on free tiers; data views still work when no model is active; scoring controls explain why they are disabled |
| Security | Per §16; no critical/high dependency vulnerabilities at release |
| Maintainability | Typed Python/TypeScript; lint/format; layered modules; ADRs |
| Observability | Structured logs with request ids; latency/error metrics; active model versions in `/health` |
| Reproducibility | Seeded training, pinned dependencies, dataset checksums, model cards with commit hash |
| Data integrity | Idempotent ingestion/scoring; transactional writes; versioned migrations |
| Accessibility | WCAG AA |

---

## 19. Project Folder Structure (Monorepo)

```
ai-predictive-maintenance/
├── README.md · LICENSE · docker-compose.yml · Makefile
├── .github/workflows/                # ci.yml, deploy.yml
├── docs/  PRD.md · architecture.md · api.md · runbook.md · datasets.md · responsible_use.md · model_cards/
├── frontend/src/  api/ · components/ · features/ · pages/ · hooks/ · lib/ · routes/ · tests/
├── backend/
│   ├── pyproject.toml · Dockerfile · alembic/
│   └── app/  main.py · core/ · api/v1/ · schemas/ · models/ · repositories/
│           · services/ (ingestion, compatibility, scoring, health_indicator, alerts, recommendations, explanations, workflow)
│           · adapters/ (interface + cmapss_fd001_csv)
│           · ml_runtime/ (bundle loader, ModelPredictor, explainers)
│           · cli.py (register-model, activate-model, create-user, seed)
│           · tests/
├── ml/  configs/ (feature_config.yaml, training configs) · notebooks/ · src/ (data, features, models, evaluation, explain, pipelines) · artifacts/ (git-ignored) · tests/
├── database/  seeds/ · sample_data/   # compatible, perturbed and incompatible sample CSVs
└── scripts/  prepare_cmapss.py · seed_admin.py · seed_demo.py
```

---

## 20. Development Roadmap

Phases 1–9 deliver the MVP in **vertical slices** (something demoable at the end of each phase). Phase 10 is post-MVP.

| Phase | Tasks | Deliverables | Depends on | Definition of Done |
|---|---|---|---|---|
| **1. Dataset & ML exploration** | Verify FD001/AI4I sources and licences; `prepare_cmapss.py`; EDA; candidate horizons H; leakage checklist; baselines | Notebooks, `datasets.md`, measured baseline table | None | Label rule and H-selection procedure documented; baselines rerunnable |
| **2. ML pipeline** | Feature config; splits; Isolation Forest vs. statistical baseline; Logistic → RF → XGBoost/LightGBM; calibration; threshold; reference stats; bundle, model card, evaluation record (metrics + curves) | Bundle, model card, evaluation artifacts | 1 | One command trains/evaluates; leakage tests pass; bundle loads in a clean env |
| **3. Backend foundation** | FastAPI skeleton, auth/RBAC, machines, adapter layer + FD001 adapter, upload/validation, compatibility check, jobs | OpenAPI spec | 2 (stub allowed) | Auth matrix passes; incompatible CSV rejected with actionable errors |
| **4. Database & model metadata** | Full schema/migrations; `register-model`/`activate-model` CLI with card + evaluation checks; audit log | Migrations, ER diagram | 3 | Fresh DB builds; activation blocked without card/evaluation |
| **5. Inference & workflow services** | Scoring with lineage; health indicator; anomaly episodes; reliability indicators; alerts; recommendations; maintenance workflow and status updates | Scoring runs end to end | 2, 4 | Idempotent scoring; alert lifecycle tests pass |
| **6. Frontend** | Shell, auth, dashboard, machines, details, alerts, datasets/wizard, **Model Performance**, settings, About; four data states | Responsive UI | 3, 5 | All MVP pages with states at three breakpoints |
| **7. Explanations & lineage UI** | Explainer, trend facts, templates, panel, "How was this prediction generated?", contribution breakdown | Explanation payload + UI | 2, 5, 6 | Every sentence traceable to stored numbers |
| **8. Demo mode & integration** | `seed_demo` with selection rule and labels; reset; sample CSVs; e2e journey test | Reproducible demo | 5–7 | §7.1/§7.2 pass in automated tests |
| **9. Testing, hardening, deployment** | §21 strategy; security review; deploy Vercel + Render/Railway + managed PG; README per §6.1 | Public URL, CI green | 8 | §26 checklist passes in production |
| **10. V2/EXP** | §22 in priority order | Per-feature specs | 9 | Each meets its own criteria without regressing MVP tests |

---

## 21. Testing Strategy

| Type | Scope |
|---|---|
| **Unit** | Health-indicator determinism and boundaries; band contiguity; alert rules; recommendation rules; explanation templates; adapter mapping; machine status transitions |
| **API** | Every endpoint: happy path, RBAC matrix, validation/error cases; OpenAPI contract tests |
| **ML** | Seeded determinism; **leakage tests**; feature schema; sanity (beats baselines; probabilities in [0,1]); calibration check; predictor-interface contract test; metrics regression with tolerance |
| **No-fabrication tests** | Model Performance renders only `model_evaluations` data; "Model evaluation not available." with none; static check that no metric literals exist in frontend/backend/seed code; UI shows original C-MAPSS sensor identifiers only |
| **Data validation** | Fixtures for missing, invalid, duplicate, unsorted, empty, oversized, malformed and encoding-edge files; nothing ingested on failure |
| **Compatibility** | Table-driven tests for every FR-6 check, AI4I rejection, range/unit mismatch, preprocessing/feature-config mismatch; scoring blocked; re-check at scoring |
| **Lineage & models** | Every prediction has non-null lineage fields (incl. schema mapping hash and horizon); activation blocked without card/evaluation; one-active-per-task |
| **Integration** | Upload → validate → compatibility → ingest → score → alert → dashboard on real PostgreSQL; idempotent re-scoring |
| **End-to-end** | Playwright test of §7.1 and §7.2 on seeded data (including workflow and machine status update) |
| **Frontend** | Component state tests; charts; forms; accessibility (axe) |
| **Security** | Auth bypass/escalation, JWT tampering, rate limits, CSV-injection and oversized uploads, SQLi/XSS probes, dependency/secret scans |

CI gates: lint, type check, unit/API/ML/compatibility tests, security scans; deploy only on green.

---

## 22. Post-MVP: V2 and Experimental Features

| Feature | Tier | Notes |
|---|---|---|
| RUL prediction, uncertainty, RUL charts, RUL health component | V2 | Capped RUL target; gradient boosting first |
| Simulated streaming/replay | V2 | Reuses the sequential scoring path |
| Automated retraining; drift detection | V2 | Retraining never auto-activates |
| Model comparison UI; advanced model registry (UI activation, stages, rollback UI) | V2 | |
| Additional adapters (AI4I, Azure PdM, bearing) and failure-mode classification | V2 | Real-motor data via adapters + separate validation |
| Email notifications; low-RUL alerts; maintenance scheduling | V2 | |
| Multi-dataset fleet analytics; fleet health trend over time | V2 | |
| Deep learning (MLP/LSTM/GRU); One-Class SVM; frequency-domain features | V2 | Adopt only if they beat baselines |
| Users UI, Viewer role, refresh tokens, password reset, recommendation-rule and threshold editing UI | V2 | |
| Job queue, object storage, inference service; global/precomputed SHAP views | V2 | |
| Transformers; autoencoders/LSTM-autoencoders; conversational AI/NL queries; digital twin; conformal prediction | EXP | Never block MVP; LLM is read-only over computed data, never used for prediction |
| Live sensor/IoT integration | Future | Out of scope |

---

## 23. Success Metrics

All targets are placeholders to fill after baselines are measured; no values are claimed here.

| Category | Metric | Target |
|---|---|---|
| Failure prediction | Precision/recall at chosen threshold (test engines); PR-AUC vs. logistic baseline | `[TBD]`; must exceed baseline |
| Calibration | Brier/ECE; reliability curve | `[TBD]` |
| Alert quality | False alarms per engine; median warning lead time | `[TBD]` |
| Anomaly detection | FPR on healthy held-out data; vs. statistical baseline | FPR at calibrated target `[X%]` |
| Reliability | Share of held-out predictions flagged `reduced` | `[TBD]` |
| Latency | Inference and API p95 | `[TBD]` |
| Dashboard | Time to interactive | `[TBD]` |
| Workflow | §7.1 completion in usability test (≥ 5 users) | `[TBD]` |
| Integrity | Predictions with complete lineage | 100% by design |

---

## 24. Resume Value

| Skill | Evidence |
|---|---|
| Machine learning / AI | Leakage-safe classification, calibration, threshold selection, anomaly detection vs. baseline |
| Time-series analysis | Past-only rolling/trend features; group- and time-aware evaluation on simulated run-to-failure data |
| Explainable AI | SHAP/linear contributions plus trend facts |
| Python / FastAPI / REST | Typed API, RBAC, jobs, uploads |
| React | Dashboard, wizard, workflow UI, Model Performance visualizations |
| PostgreSQL | Constraints, partial unique indexes, lineage schema |
| MLOps / software engineering | Model cards, evaluation records, lineage, compatibility gate, CI, tests, deployment |

**Resume bullets** (replace `[ ]` only with measured results; delete anything unsupported)
1. Built a full-stack predictive-maintenance analytics platform (React, FastAPI, PostgreSQL) demonstrated on NASA C-MAPSS simulated turbofan data, with anomaly detection, failure-probability prediction, an explainable health indicator and a human-in-the-loop maintenance workflow, deployed with a public demo.
2. Developed a leakage-safe time-series pipeline (group-aware splits, past-only features, calibrated gradient boosting) reaching `[PR-AUC / recall @ precision]` vs. a `[baseline]` baseline on held-out engines at horizon `[H]` cycles.
3. Implemented Isolation Forest anomaly detection benchmarked against a statistical baseline at a `[X%]` false-positive rate, with prediction-reliability warnings for out-of-distribution inputs.
4. Designed model metadata, model cards, stored evaluations and end-to-end prediction lineage, with a Model Performance page and a dataset-compatibility gate that blocks inference on incompatible data.
5. Added SHAP/linear explanations and rule-based recommendations, keeping AI outputs distinct from engineer decisions; p95 API latency `[X ms]`.

---

## 25. Glossary

| Term | Definition |
|---|---|
| **As-of / data time** | Position in the dataset (cycle/timestamp) a prediction refers to; distinct from system time |
| **Adapter** | Code-defined dataset format description and mapping to canonical fields (§8.4) |
| **Schema mapping** | Saved mapping from a CSV's columns to canonical fields; part of a dataset version |
| **Model bundle** | Deployable artifact: preprocessing, model, calibrator, thresholds, reference stats, manifest |
| **Prediction horizon (H)** | Number of future operating units (cycles for FD001) the failure question covers; fixed per model version |
| **Failure probability** | Calibrated estimate of failure within the next H units |
| **Risk classification** | Display category (Low/Medium/High/Critical) from configurable probability bands |
| **Decision threshold** | Model-level probability cut-off chosen on validation data; default alert threshold |
| **Prediction reliability** | Input-vs-training-data indicator; not statistical confidence and not correctness |
| **Machine Health Indicator** | Deterministic derived 0–100 indicator (FR-10) |
| **AI prediction / AI recommendation / human action / outcome** | The four distinct stages in FR-14 |
| **Anomaly episode** | Run of consecutive anomalous points recorded as one event |
| **Scoring run** | Background job applying active models to a compatible dataset |
| **Demo data** | Seeded content labelled "Demo / Simulated Data" |
| **RUL** | Remaining Useful Life (V2 output; used internally to derive labels) |

---

## 26. MVP Definition of Done

The MVP is complete only when a user can:

1. Log in.
2. Open the seeded demo fleet.
3. View machine health.
4. Open a machine.
5. View historical sensor data.
6. View anomaly status.
7. View failure probability.
8. View the prediction explanation.
9. View the model version.
10. View model performance.
11. Receive an alert.
12. Review the recommended action.
13. Acknowledge the alert.
14. Record a maintenance action.
15. View the maintenance record.
16. Upload a compatible CSV.
17. Receive a validation report.
18. Run inference on compatible data.
19. Be blocked from inference when data is incompatible.
20. Use the deployed application without local setup.

**Verification notes.** Items 1–15 and 20 are performed as the demo Engineer and covered by the automated end-to-end test (§21). Items 16–19 are performed by an Admin using the repository sample CSVs (compatible, perturbed, incompatible); the seeded rejected AI4I sample lets any user see item 19's blocking behavior without uploading. All values shown come from the real pipeline and stored evaluations; if these workflows pass end to end, the MVP is complete.

---

## Final Revision Summary

### Major changes made
- **Positioning** now separates product vision (motors, pumps, compressors, turbines), MVP demonstration domain (NASA C-MAPSS FD001, simulated turbofan data, not validated on real machines) and future industrial domain (via adapters), applied consistently in the executive summary, vision, dashboard label, dataset section, README requirements, limitations and Demo Mode.
- **Removed invented sensor semantics:** original C-MAPSS identifiers are displayed everywhere; sensor categories, "vibration/temperature" wording and component-specific recommendations were removed; a physical mapping requires a cited source.
- **Prediction target** defined precisely: failure within configurable horizon H (cycles), H selected during development and stored per model version; outputs are probability, horizon, risk classification, timestamp/cycle and model version.
- **New Model Performance page** backed by a `model_evaluations` table, with "Model evaluation not available." when no evaluation exists.
- **Demo Mode is the primary first-run path** with a deterministic, non-faked seed (Healthy, Warning, Critical machines) and a new first-run journey; CSV onboarding is a separate Admin workflow.
- **Maintenance workflow** separates AI prediction, AI recommendation, human decision/action and outcome in data and UI, and defines the machine-status update.
- **Lineage strengthened** with schema mapping hash, preprocessing version and prediction horizon, exposed as "How was this prediction generated?".
- **Compatibility check strengthened** (feature ordering/mapping, preprocessing and dataset/model compatibility) with Expected/Found/How-to-fix output.
- **Health score renamed "Machine Health Indicator"** with an exact formula and four-row contribution breakdown.
- **Complexity trimmed:** UI model activation, Users UI and editable reliability/severity settings moved out of the MVP; models are registered/activated via CLI.
- **Consistency audit fixes:** renamed DB/API fields (`health_indicator`), removed the fleet trend and RUL widgets from MVP, clarified reliability warnings (MVP) vs. drift detection (V2), and added README requirements.

### MVP features
Seeded demo environment; authentication (Admin/Engineer); fleet dashboard; machine detail; dataset onboarding, validation and schema mapping; compatibility check; Isolation Forest + statistical-baseline anomaly detection; failure prediction with horizon H; Machine Health Indicator; explainable predictions; generic maintenance recommendations; in-app alerts; maintenance action recording; model metadata/versions/lineage; Model Performance page; reliability warnings; end-to-end deployment.

### V2 features
RUL; simulated replay; automated retraining; drift detection; model comparison UI and advanced registry; email; low-RUL alerts; scheduling; multi-dataset fleet analytics and fleet trends; deep learning (MLP/LSTM/GRU); One-Class SVM; frequency-domain features; additional adapters and failure-mode classification; Users UI, Viewer role, refresh tokens; job queue and object storage.

### Experimental features
Transformers; autoencoders and LSTM-autoencoders; conversational AI/natural-language queries; digital twin; conformal prediction. (Live IoT integration is out of scope.)

### Important product limitations
Public simulated/synthetic data only; not validated on real industrial machines; C-MAPSS is turbofan data, not motor telemetry, with sensors unmapped to physical meanings; predictions are statistical estimates; the health indicator is derived, not standardized; reliability warnings do not measure correctness; not a certified safety system; no physical diagnosis; human decisions govern all maintenance.

### Key assumptions
FD001 and its documentation remain available and licence-compatible for demo sample files; a suitable horizon H can be chosen from candidate values during model development; a single-instance, free-tier-friendly deployment is acceptable for the demo; the developer registers and activates models via CLI in the MVP; performance targets are unknown until baselines are measured and are left as placeholders.