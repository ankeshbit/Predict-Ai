# Production Deployment Guide

This document describes how to deploy the Predict-Ai platform across Vercel (Frontend), Render or Railway (Backend), and Neon (Database).

---

## 1. Architecture Overview

- **Frontend**: Vite React SPA hosted on Vercel.
- **Backend**: Containerized FastAPI service hosted on Render or Railway.
- **Database**: Neon Serverless PostgreSQL.
- **ML Artifacts**: Packaged inside the backend container image or mounted via persistent disk.

---

## 2. Environment Variables Summary

### Backend (Render / Railway)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | Pooled Neon PostgreSQL URL (via PgBouncer) | `postgresql+psycopg://user:pass@ep-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require` |
| `DATABASE_URL_DIRECT` | Direct Neon connection URL for Alembic migrations | `postgresql+psycopg://user:pass@ep-direct.us-east-2.aws.neon.tech/neondb?sslmode=require` |
| `SECRET_KEY` | Hex token for signing JWT access tokens | `a79f3b89012cd...` |
| `ENVIRONMENT` | `production` or `staging` | `production` |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `https://predict-ai.vercel.app` |
| `MODEL_ARTIFACTS_DIR` | Directory containing registered bundles | `/app/model_artifacts` |

### Frontend (Vercel)
| Variable | Description | Example |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL pointing to deployed FastAPI backend | `https://predict-ai-backend.onrender.com` |

---

## 3. Release Sequence

1. **Alembic Database Migration**:
   ```bash
   alembic upgrade head
   ```
2. **Model Bundle Registration & Activation**:
   Run registration inside the container or within a venv matching the bundle's Python pins:
   ```bash
   docker compose run --rm backend python -m app.cli register-model --bundle-path model_artifacts/<model_version>
   ```
3. **Demo Data Seed**:
   Seeder re-runs `score_trajectory` in the backend, asserts parity with `demo_reference_scores.csv`, and populates distinct engines for Healthy, Warning, and Critical:
   ```bash
   docker compose run --rm backend python -m app.cli seed-demo --bundle-path model_artifacts/<model_version>
   ```
