"""
FastAPI Main Application Entrypoint for Predict-Ai (PrediCore)
"""

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.alerts import router as alerts_router
from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.demo import router as demo_router
from app.api.v1.health_config import router as health_config_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.machines import router as machines_router
from app.api.v1.maintenance import router as maintenance_router
from app.api.v1.models import router as models_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.settings import admin_router, settings_router
from app.core.config import settings
from app.core.db import engine
from app.core.errors import (
    AppError,
    app_error_handler,
    generic_exception_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.ml.verify_artifacts import verify_all
from app.schemas.common import HealthStatus

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def verify_active_model_artifacts():
    """Verifies registered model artifacts at startup.
    Refuses to start on any manifest tampering or library version mismatch.
    """
    artifacts_base = Path(settings.MODEL_ARTIFACTS_DIR)
    if not artifacts_base.is_absolute():
        artifacts_base = Path(__file__).resolve().parent.parent / settings.MODEL_ARTIFACTS_DIR

    if artifacts_base.is_dir():
        candidate_bundles = [
            d for d in artifacts_base.iterdir()
            if d.is_dir() and (d / "metadata" / "artifact_manifest.json").is_file()
        ]
        strict = (settings.ENVIRONMENT != "testing" and os.environ.get("TESTING") != "1")
        for bundle in candidate_bundles:
            verify_all(bundle, strict_versions=strict)
            logger.info("Strict model bundle verification PASSED for '%s' (manifest checksums + Python 3.12 library versions).", bundle.name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks: run manifest + library-version verification
    verify_active_model_artifacts()
    yield
    # Shutdown tasks
    engine.dispose()


app = FastAPI(
    title="Predict-Ai API",
    description="AI-Powered Predictive Maintenance & Machine Intelligence Platform",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Exception Handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
    except Exception as e:
        logger.exception("Unhandled error in request: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact system administration.",
                    "details": str(e) if settings.DEBUG else None,
                }
            },
            headers={"X-Request-ID": request_id},
        )


# API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(machines_router, prefix="/api/v1")
app.include_router(datasets_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(scoring_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(anomalies_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(maintenance_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")
app.include_router(health_config_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")


@app.get("/health", response_model=HealthStatus, tags=["System"])
def health_check():
    """
    Health check endpoint reporting database connectivity without crashing on cold starts.
    """
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"degraded: {str(e)[:100]}"

    return HealthStatus(
        status="ok" if "connected" in db_status else "degraded",
        environment=settings.ENVIRONMENT,
        database=db_status,
        version="3.0.0"
    )
