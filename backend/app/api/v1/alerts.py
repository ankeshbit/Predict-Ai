"""
Alerts API router: listing active and historical alerts, human engineer acknowledgment, and resolution.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models.entities import Alert, User
from app.schemas.alerts import AlertAcknowledgeRequest, AlertListResponse, AlertResolveRequest, AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
def list_alerts(
    machine_id: Optional[uuid.UUID] = Query(None, description="Filter by machine ID"),
    status: Optional[str] = Query(None, description="Filter by alert status: open, acknowledged, resolved"),
    severity: Optional[str] = Query(None, description="Filter by severity: warning, critical"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists alerts across the fleet with filtering and pagination."""
    stmt = select(Alert)
    if machine_id:
        stmt = stmt.where(Alert.machine_id == machine_id)
    if status:
        stmt = stmt.where(Alert.status == status)
    if severity:
        stmt = stmt.where(Alert.severity == severity)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Alert.created_at.desc()).offset(offset).limit(limit)).all()

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        total=total,
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: uuid.UUID,
    payload: Optional[AlertAcknowledgeRequest] = None,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Human engineer acknowledges an open alert."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError(message=f"Alert with id {alert_id} not found")

    if alert.status == "resolved":
        raise ConflictError(message="Cannot acknowledge an alert that has already been resolved.")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by_user_id = current_user.id

    db.commit()
    db.refresh(alert)
    return AlertResponse.model_validate(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: uuid.UUID,
    payload: Optional[AlertResolveRequest] = None,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Human engineer resolves an alert."""
    alert = db.get(Alert, alert_id)
    if not alert:
        raise NotFoundError(message=f"Alert with id {alert_id} not found")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by_user_id = current_user.id

    db.commit()
    db.refresh(alert)
    return AlertResponse.model_validate(alert)
