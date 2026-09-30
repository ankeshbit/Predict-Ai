# Predict-Ai (PrediCore)

**Industrial Predictive Maintenance & Machine Intelligence Analytics Platform**

Predict-Ai is a 100% software-based predictive maintenance analytics platform demonstrating end-to-end ML engineering: leakage-safe time-series modeling, probability calibration, SHAP explainability, lineage tracking, dataset compatibility safeguards, typed REST API, and an industrial-grade dashboard.

---

## 1. Domain & Mandatory Disclosures

### Demonstration Domain
- **Dataset**: NASA C-MAPSS FD001 (Commercial Modular Aero-Propulsion System Simulation).
- **Domain Clarification**: C-MAPSS FD001 is **simulated turbofan aero-engine degradation data**, not real industrial plant data, motor telemetry, or pump data.
- **Sensor Identifiers**: All sensors are displayed exclusively by their original identifiers (`sensor_1` \dots `sensor_21`) and operating settings (`op_setting_1` \dots `op_setting_3`). No physical semantics are asserted without an authoritative mapping adapter.

### Mandatory Limitations (PRD §6)
1. The MVP is an analytics demonstration on public simulated benchmarks and has not been certified or validated on physical industrial machines in active service.
2. C-MAPSS FD001 is simulated turbofan engine data. AI4I 2020 is synthetic tabular data. Neither represents real plant conditions.
3. Sensors are shown with original identifiers (`sensor_1` \dots `sensor_21`); no physical meaning is asserted for them in the MVP.
4. Predictions are statistical estimates, not guaranteed failure events. Low probability does not guarantee safety; high probability does not confirm a fault.
5. The system is not a certified industrial safety system and must not be the sole basis for safety-critical decisions.
6. The system does not physically diagnose or repair equipment. Recommendations are decision support; humans decide and act.
7. The Machine Health Indicator is a derived product indicator, not a standardized or scientifically validated industrial health measurement.
8. Prediction Reliability indicators compare inputs to training data; they do not measure whether a prediction is correct.
9. Real deployment would require representative domain data, new model development, and re-validation. Performance may change across machines and operating conditions.
10. All demo content is explicitly labelled `"Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"`.

---

## 2. Human Authority & Workflow Separation
The platform enforces strict separation across 4 chronological stages:
1. **AI Prediction**: Mathematical risk score $P(\text{Fail} \le H)$ and unsupervised anomaly score $s_{\text{anom}}$.
2. **AI Recommendation**: Rule-based decision-support advisory (not a diagnosis).
3. **Engineer Decision & Action**: Human engineer review (*Accepted*, *Modified*, *Declined*) with mandatory engineering rationale, followed by physical maintenance logging.
4. **Maintenance Outcome**: Closed-loop operational verification (*Resolved*, *No Issue Found*, *Unresolved*).

---

## 3. Demo Credentials

- **Reliability Engineer**:
  - Email: `engineer@predicore.internal`
  - Passcode: `EngineerSecurePass123!`
  - Scope: Telemetry monitoring, alert triage, maintenance recording.
- **System Administrator**:
  - Email: `admin@predicore.internal`
  - Passcode: `AdminSecurePass123!`
  - Scope: Machine onboarding, schema mapping, scoring runs, health formula weights, system audit logs.

---

## 4. How to Reproduce Training in Google Colab

1. Upload raw NASA C-MAPSS FD001 files (`train_FD001.txt`, `test_FD001.txt`, `RUL_FD001.txt`) to Google Drive at `My Drive/predict-ai/data/`.
2. Open `ml/notebooks/02_train_evaluate_export.ipynb` in Google Colab.
3. Execute all cells to perform:
   - Grouped leakage-safe train/test splits by engine unit.
   - Isolation Forest anomaly detector fitting on early-life healthy cycles.
   - GroupKFold hyperparameter optimization and Platt probability calibration.
   - Evaluation on held-out engines emitting `evaluation.json`.
   - Export of `bundle_v1.0.0.zip`.
4. Detailed steps are documented in [docs/colab_runbook.md](docs/colab_runbook.md).

---

## 5. How to Register a Model

Once a model bundle is generated, register it with the backend CLI:

```bash
# 1. Extract bundle to backend/model_artifacts/
cp -r bundle_v1.0.0/ backend/model_artifacts/bundle_v1.0.0/

# 2. Register model (validates SHA-256 checksums, library versions, model card, and evaluation)
cd backend
python -m app.cli register-model model_artifacts/bundle_v1.0.0

# 3. Activate model for serving
python -m app.cli activate-model failure_lgb_v1.0.0
```

---

## 6. Scope Boundaries & Non-Goals (Not Implemented)

Per PRD §2 and §5, the following are non-goals for this MVP:
- No live streaming, WebSockets, or hardware/IoT edge agents.
- No LLMs in the prediction or inference path.
- No microservices, Kubernetes, Celery, or Redis.
- No multi-tenancy or user management UI.
- No UI-triggered model training or fitting.
- Any features marked V2/EXP in the PRD (such as frequency-domain FFT features, deep learning LSTM/Transformers, automated RUL regression, and multi-operating condition adapters) are deferred.
