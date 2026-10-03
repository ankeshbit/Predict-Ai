"""
Anomalies API Router (PRD §14.4)
"""

import uuid
from typing import Optional

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import Anomaly, Machine, User
from app.schemas.anomalies import AnomalyListResponse, AnomalyResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(tags=["Anomalies"])


@router.get("/anomalies", response_model=AnomalyListResponse)
def list_anomalies(
    machine_id: Optional[uuid.UUID] = Query(None, description="Filter by machine ID"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, warning, critical"),
    is_anomaly: Optional[bool] = Query(None, description="Filter flagged anomalies only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists anomaly episodes and flagged readings with filtering and pagination."""
    stmt = select(Anomaly)
    if machine_id:
        stmt = stmt.where(Anomaly.machine_id == machine_id)
    if severity:
        stmt = stmt.where(Anomaly.severity == severity)
    if is_anomaly is not None:
        stmt = stmt.where(Anomaly.is_anomaly == is_anomaly)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Anomaly.detected_at.desc()).offset(offset).limit(limit)).all()

    return AnomalyListResponse(
        items=[AnomalyResponse.model_validate(a) for a in items],
        total=total,
    )


@router.get("/machines/{machine_id}/anomalies", response_model=AnomalyListResponse)
def list_machine_anomalies(
    machine_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists anomaly records for a specific machine."""
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine {machine_id} not found")

    stmt = select(Anomaly).where(Anomaly.machine_id == machine_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Anomaly.cycle.desc()).offset(offset).limit(limit)).all()

    return AnomalyListResponse(
        items=[AnomalyResponse.model_validate(a) for a in items],
        total=total,
    )
