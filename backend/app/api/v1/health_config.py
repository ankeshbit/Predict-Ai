"""
Health Indicator Configuration API router: view and configure deterministic breakdown weights.
"""

from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import HealthIndicatorConfig, User
from app.schemas.health_config import HealthConfigResponse, HealthConfigUpdateRequest
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/health-config", tags=["Health Indicator Configuration"])


@router.get("", response_model=HealthConfigResponse)
def get_active_health_config(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves the active Machine Health Indicator configuration."""
    cfg = db.scalar(
        select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
    )
    if not cfg:
        raise NotFoundError(message="Active health indicator configuration not found.")
    return HealthConfigResponse.model_validate(cfg)


@router.put("", response_model=HealthConfigResponse)
def update_health_config(
    payload: HealthConfigUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates the active Machine Health Indicator parameters (Admin only)."""
    cfg = db.scalar(
        select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
    )
    if not cfg:
        raise NotFoundError(message="Active health indicator configuration not found.")

    if payload.anomaly_weight is not None:
        cfg.anomaly_weight = payload.anomaly_weight
    if payload.data_quality_penalty is not None:
        cfg.data_quality_penalty = payload.data_quality_penalty
    if payload.trend_enabled is not None:
        cfg.trend_enabled = payload.trend_enabled

    db.commit()
    db.refresh(cfg)
    return HealthConfigResponse.model_validate(cfg)
