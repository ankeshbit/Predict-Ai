# Predict-Ai / PrediCore — Build Progress & Status Tracking

This document tracks completed phases, architectural decisions, and open questions across the 9-phase build plan.

---

## Current Status: Phase 0 Completed / Ready for Gate Approval

### Phase Summary Table

| Phase | Description | Status | Verification & Test Gate |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Orientation, Scaffolding, & Specs** | **Complete** | Layout created, .gitignore, docker-compose, CI, docs initialized, linters green. |
| **Phase 1** | **Shared ML Library (`pdm_core`) & Bundle Contract** | **Complete (Stopped at Gate H1)** | 18 unit tests passed: causality/no-leakage, grouped splits, evaluation schema, bundle CLI validate. |
| **Phase 2** | Backend Foundation on Neon PostgreSQL | Queued | Migrations, auth, models, CRUD, RBAC test matrix. |
| **Phase 3** | Adapters, Upload, Validation, Compatibility | Queued | Table-driven compatibility tests, 11 FR-6 checks. |
| **Phase 4** | Model Registry, Scoring Engine, Workflow | Pending Gate H2 | Real Colab bundle loaded; idempotent scoring; health indicator. |
| **Phase 5** | Seeded Demo Mode | Queued | Held-out C-MAPSS engines scored deterministically; reset endpoint. |
| **Phase 6** | Frontend Integration (TanStack Query + Router) | Queued | Wire API client, replace mockData, enforce real RBAC and error handling. |
| **Phase 7** | Testing, Security, & Hardening | Queued | Vitest, Pytest, Playwright e2e, static metric leakage guardrails. |
| **Phase 8** | Deployment, Docker, & Documentation | Pending Gate H3 | Multi-stage Dockerfile, Vercel/Render deployment runbooks. |

---

## Phase 1 Deliverables & Verification
1. **`pdm_core.data`**: C-MAPSS FD001 data loader (`load_fd001_raw`), train per-cycle RUL calculator (`compute_train_rul`), test per-cycle RUL calculator (`compute_test_rul`).
2. **`pdm_core.labels`**: Binary failure risk labeling (`assign_binary_labels`) over arbitrary horizon $H$.
3. **`pdm_core.features`**: Past-only causal feature engineering (`extract_features`, `get_feature_names`, `default_config.yaml`). Strictly tested with zero future data leakage.
4. **`pdm_core.splits`**: Engine-grouped splitting (`engine_grouped_split`, `get_engine_split_ids`) with strict disjointness assertions.
5. **`pdm_core.evaluation`**: Evaluation metrics and curves calculator (`compute_evaluation`, `save_evaluation_json`) computing PR-AUC, ROC-AUC, Brier score, ECE, calibration bins, downsampled curves ($\le 50$ points), and feature importances.
6. **`pdm_core.bundle`**: Cryptographic hasher (`compute_file_sha256`), bundle writer (`write_complete_bundle`, `write_failure_risk_bundle`, `write_anomaly_bundle`), bundle validator (`validate_model_bundle`), and CLI (`python -m pdm_core.bundle validate <path>`).
7. **`pdm_core.explain`**: TreeSHAP (`compute_tree_shap`) and linear contribution (`compute_linear_contribution`) helpers.
8. **Notebook Contract**: Published `docs/notebook_contract.md` specifying imports, exports, and workflow template for external Colab training.

---

## Current Status: Stopped at Gate H1
- Waiting for human training notebook / model bundle export (`bundle_<version>`).
- In Phase 4, the platform will run `python -m pdm_core.bundle validate <path>` prior to database model registration.
