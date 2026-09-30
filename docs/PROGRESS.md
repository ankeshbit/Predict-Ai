# Predict-Ai / PrediCore — Build Progress & Status Tracking

This document tracks completed phases, architectural decisions, and open questions across the 9-phase build plan.

---

## Current Status: Phase 0 Completed / Ready for Gate Approval

### Phase Summary Table

| Phase | Description | Status | Verification & Test Gate |
| :--- | :--- | :--- | :--- |
| **Phase 0** | **Orientation, Scaffolding, & Specs** | **Complete** | Layout created, .gitignore, docker-compose, CI, docs initialized, linters green. |
| **Phase 1** | `pdm_core` package + Colab Notebooks | Pending Gate H1 | Local synthetic tests for leakage, causality, bundle round-trip. |
| **Phase 2** | Backend Foundation on Neon PostgreSQL | Queued | Migrations, auth, models, CRUD, RBAC test matrix. |
| **Phase 3** | Adapters, Upload, Validation, Compatibility | Queued | Table-driven compatibility tests, 11 FR-6 checks. |
| **Phase 4** | Model Registry, Scoring Engine, Workflow | Pending Gate H2 | Real Colab bundle loaded; idempotent scoring; health indicator. |
| **Phase 5** | Seeded Demo Mode | Queued | Held-out C-MAPSS engines scored deterministically; reset endpoint. |
| **Phase 6** | Frontend Integration (TanStack Query + Router) | Queued | Wire API client, replace mockData, enforce real RBAC and error handling. |
| **Phase 7** | Testing, Security, & Hardening | Queued | Vitest, Pytest, Playwright e2e, static metric leakage guardrails. |
| **Phase 8** | Deployment, Docker, & Documentation | Pending Gate H3 | Multi-stage Dockerfile, Vercel/Render deployment runbooks. |

---

## Phase 0 Decisions & Deliverables
1. **Repository Layout**: Initialized modular layout per §6 with `ml/`, `backend/`, `frontend/`, `docs/`, `database/`, and `scripts/`.
2. **Database Engine**: Primary runtime uses Neon Serverless PostgreSQL with pooled connection string (`prepare_threshold=None`) and direct string for migrations. Local Docker Compose configured for local test runners.
3. **ML Workflow Boundary**: Enforced complete separation of training and inference. All training logic encapsulated in `ml/src/pdm_core/` for Google Colab; backend runtime strictly loads checksum-verified bundles.
4. **Guardrails**: Initialized `AGENTS.md` and static guardrail script to ensure zero hardcoded metrics and no physical sensor name descriptions exist in application code.

---

## Pre-Phase 1 Action Items Completed
1. **Enhanced CI Guardrail**: `scripts/check_guardrails.py` now scans `frontend/src` (including `mockData`), `backend/app`, and `ml/src/pdm_core` for physical sensor terms (`thermal`, `temperature`, `vibration`, `pressure`, `motor`). Fails unless explicitly registered under `ALLOWLIST_PHASE_6_TODO`.
2. **Environment Matrix & Python Reconcile**: Documented local test environment deviation (Python 3.10.0 host vs planned 3.11/3.12). Pinned `numpy==1.26.4` to prevent binary incompatibility with scikit-learn 1.4.2 and XGBoost 2.0.3 under NumPy 2.x.
3. **Configurable DB Timeout**: Added `DB_CONNECT_TIMEOUT` env var (defaults to 10s for Neon cold-starts, overridable to 2s in tests).
4. **Model Bundle Storage**: ADR-05 established. Active production model bundles (`.joblib`, `.json`, `.yaml`) are un-ignored and tracked directly in Git under `backend/model_artifacts/` for self-contained CI and Docker builds.
5. **Sample Data Provenance**: Confirmed all CSVs in `database/sample_data/` are synthetic test fixtures. Renamed to `*_synthetic_test_fixture.csv` and documented in `docs/datasets.md`.
6. **PRD Alignment**: Confirmed `docs/PRD.md` sections match PRD v3.0, including §8.4 Telemetry Schema and §26 Definition of Done.

---

## Open Questions & Awaiting Gate Trigger
- Awaiting user command **"Go"** to initiate Phase 1 (`pdm_core` package and Colab notebooks).
