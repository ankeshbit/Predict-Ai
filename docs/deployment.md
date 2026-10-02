# Production Deployment Guide — Predict-Ai (PrediCore)

This guide covers end-to-end production deployment: Neon PostgreSQL, Render/Railway (backend), and Vercel (frontend). All commands are exact and copy-pasteable.

---

## 1. Architecture Overview

| Tier | Technology | Host |
|:---|:---|:---|
| Frontend | Vite React SPA | Vercel |
| Backend | FastAPI (Docker) | Render (or Railway) |
| Database | Neon Serverless PostgreSQL | Neon |
| ML Artifacts | Baked into backend container image | — |

---

## 2. Mandatory Environment Variables

> [!CAUTION]
> The application **refuses to start** in `ENVIRONMENT=production` if `SECRET_KEY` is shorter than 32 characters, matches any known default, or if `DATABASE_URL` points to localhost or the test database. These checks are enforced in `app/main.py::check_production_security()`.

### 2.1 Backend — Render / Railway

| Variable | Required | Description | Example / Generation |
|:---|:---:|:---|:---|
| `ENVIRONMENT` | **MANDATORY** | Must be `production` | `production` |
| `SECRET_KEY` | **MANDATORY** | Hex token ≥ 32 chars for signing JWTs. **Never use a default.** | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | **MANDATORY** | **Pooled** Neon URL (via PgBouncer). Used by the FastAPI app at runtime. | `postgresql+psycopg://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require` |
| `DATABASE_URL_DIRECT` | **MANDATORY** | **Direct** Neon URL (non-pooled). Used exclusively by Alembic migrations. | `postgresql+psycopg://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require` |
| `CORS_ORIGINS` | **MANDATORY** | Comma-separated list of allowed frontend origins | `https://predict-ai.vercel.app` |
| `MODEL_ARTIFACTS_DIR` | recommended | Path to model bundles inside container | `/app/model_artifacts` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | optional | JWT token TTL (default 60) | `60` |
| `LOG_LEVEL` | optional | `INFO` or `WARNING` for production | `INFO` |

> **Neon URL anatomy**:
> - **Pooled** (PgBouncer): hostname contains `-pooler` — use for `DATABASE_URL`
> - **Direct**: standard hostname — use for `DATABASE_URL_DIRECT` (Alembic)

### 2.2 Frontend — Vercel

| Variable | Required | Description | Example |
|:---|:---:|:---|:---|
| `VITE_API_BASE_URL` | **MANDATORY** | Base URL of the deployed FastAPI backend | `https://predict-ai-backend.onrender.com` |

---

## 3. Release Sequence — Exact Docker Commands (Neon)

Run these steps **in order** after every new deployment. The backend container image must be built and tagged first (`docker compose build backend` or pushed to a registry).

### Step 1 — Run Alembic Migrations (via `DATABASE_URL_DIRECT`)

```bash
# Uses the direct (non-pooled) Neon URL to run DDL migrations safely.
docker compose run --rm \
  -e DATABASE_URL="${DATABASE_URL_DIRECT}" \
  backend \
  alembic upgrade head
```

> [!IMPORTANT]
> Alembic **must** use `DATABASE_URL_DIRECT` (the non-pooled connection). PgBouncer in transaction mode does not support prepared statements needed by Alembic's `LOCK TABLE` DDL. The app conftest enforces this split.

### Step 2 — Register & Activate the Failure Model

```bash
# Register the XGBoost calibrated failure model bundle and set it as active.
docker compose run --rm backend \
  python -m app.cli register-model \
    --bundle-path model_artifacts/cmapss-fd001-h30-v1 \
    --activate
```

### Step 3 — Register & Activate the Anomaly Model

```bash
# Register the anomaly detector bundle and set it as active.
docker compose run --rm backend \
  python -m app.cli register-model \
    --bundle-path model_artifacts/cmapss-fd001-anomaly-v1 \
    --activate
```

> [!NOTE]
> Both model bundles must be registered before seeding demo data. Each bundle must have a complete model card and an attached evaluation record — the service will reject incomplete bundles (PRD §1.7).

### Step 4 — Seed Demo Fleet

```bash
# Seeds three deterministic demo engines (Healthy / Warning / Critical)
# by running score_trajectory through the registered model pipeline,
# asserting parity with demo_reference_scores.csv.
docker compose run --rm backend \
  python -m app.cli seed-demo \
    --bundle-path model_artifacts/cmapss-fd001-h30-v1
```

### Step 5 — Seed Default Accounts (First Deploy Only)

```bash
# Creates the initial admin and engineer accounts using passwords
# from INITIAL_ADMIN_PASSWORD and INITIAL_ENGINEER_PASSWORD env vars.
# Skip on subsequent deployments (idempotent — skips if users exist).
docker compose run --rm backend \
  python -m app.cli seed-defaults
```

> [!CAUTION]
> **Change both default account passwords immediately after the first login.** The seeded passwords are placeholders read from environment variables. In production, set `INITIAL_ADMIN_PASSWORD` and `INITIAL_ENGINEER_PASSWORD` to strong, unique values and rotate them post-deploy.

---

## 4. Vercel Deployment (Frontend)

### 4.1 Setup

1. Connect the GitHub repo to Vercel.
2. Set **Framework Preset** to `Vite`.
3. Set **Root Directory** to `frontend/`.
4. Set **Build Command** to `npm run build`.
5. Set **Output Directory** to `dist`.

### 4.2 Environment Variables (Vercel Dashboard)

| Variable | Value |
|:---|:---|
| `VITE_API_BASE_URL` | `https://predict-ai-backend.onrender.com` (or Railway URL) |

### 4.3 Deploy

```bash
# Via Vercel CLI (from frontend/ directory):
npx vercel --prod
```

### 4.4 Post-Deploy Checks

- Confirm `VITE_API_BASE_URL` resolves correctly in the browser console (Network tab → login request).
- Confirm the banner reads exactly: `Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data`.
- Confirm demo items carry the `Demo / Simulated Data` badge (PRD §1.1).

---

## 5. Render / Railway Deployment (Backend)

### 5.1 Render Setup

1. Create a new **Web Service** → connect GitHub repo.
2. Set **Root Directory** to `backend/`.
3. Set **Runtime** to **Docker** (Render will use `backend/Dockerfile`).
4. Set **Instance Type** to at least `Standard` (512 MB RAM minimum for model inference).
5. Enable **Health Check**: path `/health`, port `8000`.

### 5.2 Render Environment Variables

Add all variables from §2.1 in the **Environment** tab. Use Render's **Secret Files** or environment groups to avoid exposing `SECRET_KEY` in logs.

| Variable | Value |
|:---|:---|
| `ENVIRONMENT` | `production` |
| `SECRET_KEY` | `<generated 64-char hex token>` |
| `DATABASE_URL` | `<Neon pooled URL>` |
| `DATABASE_URL_DIRECT` | `<Neon direct URL>` |
| `CORS_ORIGINS` | `https://predict-ai.vercel.app` |
| `MODEL_ARTIFACTS_DIR` | `/app/model_artifacts` |

### 5.3 Railway Setup

1. Create a new **Service** → **Docker** → connect GitHub repo.
2. Set **Dockerfile path** to `backend/Dockerfile`.
3. Add all environment variables from §2.1 via Railway's **Variables** panel.
4. Add a **Custom Domain** or use the Railway-generated URL for `VITE_API_BASE_URL` on Vercel.

### 5.4 Post-Deploy Checks

```bash
# Confirm the health endpoint is up:
curl https://predict-ai-backend.onrender.com/health

# Expected response:
# {"status":"ok","environment":"production","database":"connected","version":"3.0.0"}
```

---

## 6. Security Hardening Checklist

| Check | How to Verify |
|:---|:---|
| `SECRET_KEY` ≥ 32 chars, not a default | App refuses to start otherwise (`RuntimeError`) |
| `DATABASE_URL` points to Neon (not localhost) | App refuses to start otherwise (`RuntimeError`) |
| Swagger UI disabled | `GET /docs` returns 404 in production |
| CORS locked to frontend origin | `CORS_ORIGINS=https://predict-ai.vercel.app` only |
| `X-Content-Type-Options: nosniff` header | Check response headers with `curl -I` |
| `X-Frame-Options: DENY` header | Check response headers with `curl -I` |
| No training code or raw weights in DB | Enforced by architecture (bundles are file-system only) |
| Admin password changed post-deploy | Manual step by system administrator |

---

## 7. Rollback

```bash
# Downgrade Alembic one revision at a time:
docker compose run --rm \
  -e DATABASE_URL="${DATABASE_URL_DIRECT}" \
  backend \
  alembic downgrade -1
```
