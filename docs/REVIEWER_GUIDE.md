# Predict-Ai (PrediCore) — Reviewer Evaluation Guide

This guide is designed for technical reviewers and evaluators to test and verify the **Predict-Ai (PrediCore)** predictive maintenance analytics platform on `localhost`.

---

## 1. Quickstart: Start Everything on Localhost

The entire system runs on `localhost` backed by a local PostgreSQL container. No cloud deployment or Neon serverless connection is required.

### Option A: PowerShell (Windows)
```powershell
.\scripts\demo.ps1
```
*Creates `.env` from template, starts PostgreSQL in Docker, applies Alembic migrations, seeds default accounts and offline ML model bundle, seeds demo machines, and starts FastAPI (`:8000`) and Vite (`:5173`). Passwords and secrets are never printed to console.*

### Option B: Makefile (Linux / macOS / Git Bash)
```bash
make demo
make dev-backend   # in terminal 1
make dev-frontend  # in terminal 2
```

### Reviewer Login Credentials
| Role | Email | Default Password (from `.env`) |
|---|---|---|
| **Administrator** | `admin@predicore.internal` | `AdminReviewer2026#Secure` |
| **Engineer** | `engineer@predicore.internal` | `Engineer2026#Secure` |

Open **http://localhost:5173** in your browser.

---

## 2. 5-Minute Walkthrough (PRD §7.1 First-Run Journey)

Follow this end-to-end journey using the seeded held-out C-MAPSS FD001 test engines:

1. **Login & Dashboard Overview**:
   - Log in as Engineer (`engineer@predicore.internal`).
   - The Overview Dashboard displays real-time health bands, probability distributions, active alerts, and priority units.
   - Note the banner: `"Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"`.
   - Note the shared live server timestamp: `"Updated [HH:MM:SS]"`.

2. **Select Critical Machine (`FD001-Unit-034`)**:
   - Navigate to **Fleet** and click `FD001-Unit-034` (or select from Priority Machines on Overview).
   - Machine detail displays:
     - **Machine Health Indicator**: Additive decomposition ($HI = 100 - \sum \text{Penalties}$) with exact point deductions for failure risk, anomaly severity, and trend.
     - **Failure Probability**: Calibrated probability estimate at horizon $H = 30$ operating cycles.
     - **Anomaly Detector**: Score vs. statistical threshold.
     - **Multivariate Telemetry Chart**: Monitored C-MAPSS channels with anomaly episode highlight.
     - **Feature Explainability (Tree SHAP)**: Local feature contributions ranking channels accelerating failure risk.

3. **Human-in-the-Loop Maintenance Lifecycle**:
   - Locate the open alert card and review the AI recommendation:
     > `"AI-generated recommendation, not a confirmed diagnosis. Verify with a qualified engineer."`
   - Click **Acknowledge Alert** (moves status `open → acknowledged`).
   - Click **Record Maintenance Action**, select decision (e.g., *Followed AI Recommendation*), enter rationale, and mark outcome as *Resolved*.
   - Submit: Operational status updates to `active`, alert resolves, and audit record is committed to PostgreSQL.

4. **Prediction Lineage Audit**:
   - Scroll to `"How was this prediction generated?"`.
   - Inspect dataset name, schema mapping SHA-256 hash, registered model version, feature window ($L=30\text{ cycles}$), and reliability warning flags.

---

## 3. Dataset Ingestion & Compatibility Gate Testing (PRD §7.3)

Navigate to **Datasets & Ingestion** (`/datasets`) as an **Admin** user to evaluate how the system handles different datasets. Three sample files are provided in `database/sample_data/`:

| File | Scenario | Expected Outcome |
|---|---|---|
| `database/sample_data/compatible_fd001_slice.csv` | Canonical FD001 slice | **PASS** (11/11 checks passed; immediate ingest & score enabled) |
| `database/sample_data/out_of_range_warn.csv` | Perturbed sensor_2 values | **WARN** (Out-of-distribution warning; requires explicit acknowledgment) |
| `database/sample_data/incompatible_non_fd001.csv` | Non-turbofan telemetry | **FAIL** (10 failed checks; scoring strictly blocked with HTTP 409) |

### Test 1: Uploading Compatible Telemetry (PASS)
1. In the 6-step wizard, upload `database/sample_data/compatible_fd001_slice.csv`.
2. **Step 2 (Profile)**: Review the non-hardcoded dataset profile card: row count, column count, delimiter (`comma`), units count, cycles per unit min/max/mean, duplicate count (`0`), and column numeric summary.
3. **Step 3 (Mapping)**: Review the auto-detected mapping table showing `100% Exact` and `95% Synonym` confidence badges.
4. **Step 4 (Compatibility)**: All 11 PRD FR-6 checks pass with green badges. Range comparison bars show all sensors within model training envelopes.
5. **Step 5 (Ingest)**: Click *Proceed to Ingestion*. Live progress bar polls `/api/v1/jobs/{id}` showing row count and units created.
6. **Step 6 (Scoring)**: Live batch model scoring executes. Final database summary reports:
   > `"X units, Y readings ingested, Z scored, W alerts opened"`
7. Click **View Scored Fleet**: Newly ingested machines appear in Fleet and Overview with `"User Upload"` badges (distinguished from seeded demo machines).

### Test 2: Uploading Out-Of-Range Telemetry (WARN)
1. Upload `database/sample_data/out_of_range_warn.csv`.
2. Proceed through Profile and Mapping to **Compatibility Gate**.
3. Summary banner displays: `"Compatibility Warning: Out-Of-Distribution Telemetry"`.
4. Check 7 (Value Range Enforcement) displays `⚠ WARNING` highlighting `sensor_2` exceeding training envelope.
5. Ingestion button is **disabled** until the engineer acknowledges:
   > `[x] I acknowledge these out-of-distribution warnings. I understand the model was not trained on these value envelopes, and that all resulting predictions will carry a REDUCED RELIABILITY flag.`
6. Upon ingestion and scoring, predictions carry `REDUCED RELIABILITY` badges across all views.

### Test 3: Uploading Completely Incompatible Telemetry (FAIL)
1. Upload `database/sample_data/incompatible_non_fd001.csv` (e.g., non-turbofan motor/plant data).
2. The compatibility gate evaluates the schema against the C-MAPSS contract and blocks scoring:
   > `"This dataset is not compatible with the selected model."`
3. Inference is strictly blocked (HTTP `409 DATASET_INCOMPATIBLE`).
4. Read the plain-language diagnosis:
   > *"Why this model cannot be used on this data: The active model bundle was trained exclusively on NASA C-MAPSS FD001 simulated turbofan engine degradation data..."*
5. Click **Download Compatibility Report** to export the structured audit report as JSON or CSV.

---

## 4. Reset Demo Controls

Click the **Reset** button in the top navigation bar (Admin only):
1. **Standard Demo Reset**: Restores seeded held-out C-MAPSS demo engines to initial baseline cycles, resetting simulated replay progress and alert statuses.
2. **Optional User Data Purge**: Check `"Also delete user-uploaded datasets and machines"`. The modal queries `/api/v1/demo/reset/preview` and displays exact counts of user datasets, machine entities, predictions, and alerts that will be purged before confirmation.

---

## 5. Model Performance Page & Metric Traceability

Navigate to **Model Evaluation** (`/performance`):
- Every metric (PR-AUC, Precision, Recall, F1, Brier Score, ECE, ROC-AUC) originates from stored `model_evaluations` records generated during offline model training.
- Hover over any metric card to inspect its technical tooltip definition.
- Each metric card displays its explicit evaluation data source (e.g., `Source: internal_test` or `Source: official_test_all_rows`).
- If no evaluation record exists for a model, the system displays `"Model evaluation not available."` (no metric literals).

---

## 6. Known Limitations and Responsible Use (from PRD §6)

1. The platform is an engineering demonstration on public datasets and has **not been validated on real industrial machines**.
2. **C-MAPSS FD001 is simulated turbofan engine degradation data**, not motor, pump, or compressor telemetry. Neither C-MAPSS nor AI4I represents live plant conditions.
3. C-MAPSS sensors are displayed with original identifiers (`sensor_1`…`sensor_21`); **no physical meaning is asserted** for them.
4. Predictions are **statistical estimates**, not guaranteed failure events. Low probability does not guarantee safety; high probability does not confirm a fault.
5. The system is **not a certified industrial safety system** and must not be the sole basis for safety-critical decisions.
6. The system **does not physically diagnose or repair equipment**. Recommendations are decision support; humans decide and act.
7. The **Machine Health Indicator** is a derived product indicator, not a standardized or scientifically validated industrial health measurement.
8. **Prediction Reliability** indicators compare inputs to training data; they do not measure whether a prediction is correct.
9. Real deployment would require representative domain data, new model development, and re-validation.
10. Demo content is labeled **"Demo / Simulated Data"**.
