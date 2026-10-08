"""
Health Indicator Configuration API router: view and configure deterministic breakdown weights.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import HealthIndicatorConfig, Setting, User
from app.schemas.health_config import (
    HealthBandInfo,
    HealthConfigResponse,
    HealthConfigUpdateRequest,
)

router = APIRouter(prefix="/health-config", tags=["Health Indicator Configuration"])


def _load_health_bands_from_db(db: Session) -> list:
    """Reads configured health bands from the database settings table."""
    setting = db.scalar(select(Setting).where(Setting.key == "health_bands"))
    if setting and setting.value and "bands" in setting.value:
        return [HealthBandInfo(**b) for b in setting.value["bands"]]
    return []


@router.get("", response_model=HealthConfigResponse)
def get_active_health_config(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves the active Machine Health Indicator configuration with bands from DB."""
    cfg = db.scalar(
        select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
    )
    if not cfg:
        raise NotFoundError(message="Active health indicator configuration not found.")

    bands = _load_health_bands_from_db(db)
    res = HealthConfigResponse.model_validate(cfg)
    return res.model_copy(update={"bands": bands})


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

    if payload.bands is not None:
        setting = db.scalar(select(Setting).where(Setting.key == "health_bands"))
        if not setting:
            setting = Setting(key="health_bands", value={"bands": [b.model_dump() for b in payload.bands]})
            db.add(setting)
        else:
            setting.value = {"bands": [b.model_dump() for b in payload.bands]}

    db.commit()
    db.refresh(cfg)
    bands = _load_health_bands_from_db(db)
    res = HealthConfigResponse.model_validate(cfg)
    return res.model_copy(update={"bands": bands})
