# Architecture & System Design Document

## 1. High-Level System Architecture

Predict-Ai (PrediCore) is structured as a decoupled analytics system:

```mermaid
graph TD
    subgraph Offline_ML [Offline ML Environment (Google Colab)]
        RawData[NASA C-MAPSS FD001 Raw / Clean] --> ColabNB[Training & Evaluation Notebooks]
        pdm_core_pkg[pdm_core Shared Package] --> ColabNB
        ColabNB --> BundleZip[Versioned Model Bundle .zip]
    end

    subgraph Storage [Persistence & Storage]
        BundleZip --> FS[backend/model_artifacts/ (Local / Volume)]
        NeonPooled[(Neon Serverless Postgres - Pooled)]
        NeonDirect[(Neon Serverless Postgres - Direct)]
    end

    subgraph Backend [FastAPI Backend Service]
        CLI[app.cli: register-model, seed-demo, create-user] --> NeonDirect
        Alembic[Alembic Migrations] --> NeonDirect
        
        API[FastAPI Web API] --> NeonPooled
        API --> Runtime[ml_runtime: Bundle Loader & Predictor]
        Runtime --> FS
        pdm_core_pkg --> Runtime
    end

    subgraph Frontend [React 19 / TypeScript SPA]
        ViteApp[PrediCore Industrial SPA] -->|REST / JSON| API
    end
```

---

## 2. Key Architecture Decisions (ADRs)

### ADR-01: Neon Serverless PostgreSQL with Pooled & Direct Connections
- **Context**: Neon uses PgBouncer in transaction pooling mode on port 6543 (pooler) and direct connections on port 5432.
- **Decision**:
  - Application runtime uses `DATABASE_URL` (pooled) with `prepare_threshold=None` in `connect_args` to disable client-side prepared statements.
  - Migrations and CLI administration use `DATABASE_URL_DIRECT` (direct connection).
  - Resiliency: `pool_pre_ping=True`, modest pool size, and retry-with-backoff for cold-start tolerance.

### ADR-02: Shared `pdm_core` Package
- **Context**: In predictive maintenance, disparities between offline training feature engineering and online serving feature engineering (training-serving skew) cause subtle, catastrophic model degradation.
- **Decision**: An installable Python package `pdm_core` in `ml/src/pdm_core/` houses all feature extraction, rolling windows, causal transforms, and model schema definitions. It is installed by Colab notebooks during training and by the FastAPI backend Docker image at runtime.

### ADR-03: Zero Training in Backend Web Process
- **Context**: Ad-hoc model fitting or online training inside a web application creates memory spikes, non-deterministic states, and severe security risks.
- **Decision**: The FastAPI backend contains **zero** training or fitting code. It exclusively loads registered model bundles, validates SHA-256 integrity, verifies installed library versions, and executes stateless inference.

### ADR-04: DB-Backed Asynchronous Jobs
- **Context**: Batch ingestion of large CSVs and scoring across multiple engines can take 5–30 seconds, exceeding HTTP request timeouts.
- **Decision**: Ingestion and scoring are handled via a database-backed `jobs` table combined with FastAPI `BackgroundTasks`. Clients poll `GET /api/v1/jobs/{id}` for completion status. No Redis or Celery broker is required for the MVP.

### ADR-05: Model Bundle Storage & Distribution Strategy
- **Context**: Model bundles consist of scikit-learn / XGBoost estimators (`.joblib`), anomaly models, preprocessors, feature configurations (`feature_config.json`), model cards (`model_card.json`), and evaluation metrics (`evaluations.json`). In FD001, each bundle is compact (~2 MB to 10 MB total).
- **Decision**:
  - **MVP / Small Bundles**: The active production model bundle is un-ignored and tracked directly in Git under `backend/model_artifacts/` (excluding staging `.zip` and `.tar.gz` archives). This ensures local development, CI test suites, and Docker builds operate completely self-contained without external network egress or GitHub token configuration.
  - **Release Distribution Alternative**: For production enterprise builds where Git repository size must be strictly minimized, bundles can be uploaded as GitHub Release assets and downloaded at Docker build time via `curl -sL https://github.com/<org>/<repo>/releases/download/<tag>/model_bundle_<version>.zip` with checksum validation against `bundle_manifest.json`.
