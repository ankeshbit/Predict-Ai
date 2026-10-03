"""
Demo Fleet Management Endpoints.

PRD FR-11: Demo data seeding and administrative reset.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.core.errors import BadRequestError, InternalServerError
from app.models.entities import ModelVersion, User
from app.services.importer import seed_demo_engines
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo Fleet"])


class DemoResetResponse(BaseModel):
    status: str
    message: str
    demo_units: Dict[str, Any]


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset demo fleet to initial seeded state (Admin only)",
)
def reset_demo_fleet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Restores the demo fleet machines (Healthy, Warning, Critical) to their
    held-out initial baseline state and reference scores.
    Clears any demo machine alerts, maintenance actions, or predictions,
    and resets their operational status to 'active'.
    Strictly restricted to Admin role.
    """
    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == "cmapss_fd001",
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    if not active_model:
        raise BadRequestError(
            code="NO_ACTIVE_MODEL",
            message="No active failure_risk model found to reset demo fleet from.",
        )

    bundle_path = Path(active_model.artifact_path)
    if not bundle_path.exists() or not (bundle_path / "demo" / "demo_units.csv").exists():
        raise BadRequestError(
            code="BUNDLE_DATA_MISSING",
            message=f"Demo artifacts not found at {active_model.artifact_path}",
        )

    try:
        results = seed_demo_engines(bundle_path, session=db)
    except Exception as exc:
        logger.error("Demo reset failed: %s", exc, exc_info=True)
        raise InternalServerError(
            code="DEMO_RESET_FAILED",
            message=f"Failed to reset demo fleet: {str(exc)}",
        )

    return DemoResetResponse(
        status="success",
        message="Demo fleet reset successfully to initial baseline.",
        demo_units=results,
    )
