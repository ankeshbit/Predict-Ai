"""
Maintenance & Human-in-the-Loop Workflow API router.
Enforces strict 4-stage lifecycle:
AI Prediction -> AI Recommendation -> Engineer Decision & Action -> Maintenance Outcome.
Machine status transitions occur strictly as workflow side-effects:
- Logging an in-progress maintenance action automatically sets machine.operational_status = 'maintenance'
- Resolving a maintenance action ('resolved' or 'no_issue_found') restores machine.operational_status = 'active'.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models.entities import Alert, Machine, MaintenanceRecord, User
from app.schemas.maintenance import (
    CompleteMaintenanceRequest,
    CreateMaintenanceRequest,
    MaintenanceListResponse,
    MaintenanceRecordResponse,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/maintenance", tags=["Maintenance & Workflow"])


@router.get("", response_model=MaintenanceListResponse)
def list_maintenance_records(
    machine_id: Optional[uuid.UUID] = Query(None, description="Filter by machine ID"),
    status: Optional[str] = Query(None, description="Filter by status: recommended, in_progress, completed, cancelled"),
    outcome: Optional[str] = Query(None, description="Filter by outcome: resolved, no_issue_found, unresolved"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists maintenance work orders and audit records."""
    stmt = select(MaintenanceRecord)
    if machine_id:
        stmt = stmt.where(MaintenanceRecord.machine_id == machine_id)
    if status:
        stmt = stmt.where(MaintenanceRecord.status == status)
    if outcome:
        stmt = stmt.where(MaintenanceRecord.outcome == outcome)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(MaintenanceRecord.started_at.desc()).offset(offset).limit(limit)).all()

    return MaintenanceListResponse(
        items=[MaintenanceRecordResponse.model_validate(m) for m in items],
        total=total,
    )


@router.post("", response_model=MaintenanceRecordResponse)
def create_maintenance_action(
    payload: CreateMaintenanceRequest,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Logs human engineer decision and initiated physical maintenance action.

    Side Effect: Machine operational status is automatically transitioned to 'maintenance'.
    """
    machine = db.get(Machine, payload.machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine {payload.machine_id} not found")

    if payload.alert_id:
        alert = db.get(Alert, payload.alert_id)
        if alert and alert.status == "open":
            alert.status = "acknowledged"
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by_user_id = current_user.id

    is_completed = payload.status == "completed" or payload.outcome in ("resolved", "no_issue_found")
    record_status = "completed" if is_completed else (payload.status or "in_progress")
    now_utc = datetime.now(timezone.utc)

    record = MaintenanceRecord(
        id=uuid.uuid4(),
        machine_id=machine.id,
        alert_id=payload.alert_id,
        issue=payload.issue or "Maintenance intervention initiated",
        recommended_action=payload.recommended_action,
        decision=payload.decision,
        decision_rationale=payload.decision_rationale,
        action_taken=payload.action_taken,
        action_type=payload.action_type or "inspection",
        status=record_status,
        outcome=payload.outcome,
        engineer_notes=payload.notes or "",
        performed_by_user_id=current_user.id,
        started_at=now_utc,
        completed_at=now_utc if is_completed else None,
    )
    db.add(record)

    # Workflow Side Effect: transition machine status
    if payload.outcome in ("resolved", "no_issue_found"):
        machine.operational_status = "active"
    else:
        machine.operational_status = "maintenance"

    # Also resolve associated alert if resolved
    if record.alert_id and payload.outcome == "resolved":
        alert = db.get(Alert, record.alert_id)
        if alert and alert.status != "resolved":
            alert.status = "resolved"
            alert.resolved_at = now_utc
            alert.resolved_by_user_id = current_user.id

    db.commit()
    db.refresh(record)
    return MaintenanceRecordResponse.model_validate(record)


@router.post("/{maintenance_id}/complete", response_model=MaintenanceRecordResponse)
def complete_maintenance_action(
    maintenance_id: uuid.UUID,
    payload: CompleteMaintenanceRequest,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Logs verified outcome and closes maintenance intervention.

    Side Effect: If outcome is 'resolved' or 'no_issue_found', machine operational status
    is automatically restored to 'active'.
    """
    record = db.get(MaintenanceRecord, maintenance_id)
    if not record:
        raise NotFoundError(message=f"Maintenance record {maintenance_id} not found")

    if record.status == "completed":
        raise ConflictError(message="Maintenance action has already been completed.")

    record.status = "completed"
    record.outcome = payload.outcome
    record.completed_at = datetime.now(timezone.utc)
    if payload.engineer_notes:
        record.engineer_notes = f"{record.engineer_notes}\n[Completion Note]: {payload.engineer_notes}".strip()

    machine = db.get(Machine, record.machine_id)
    if machine:
        if payload.outcome in ("resolved", "no_issue_found"):
            # Workflow Side Effect: restore machine to active
            machine.operational_status = "active"

    # Also resolve associated alert if resolved
    if record.alert_id and payload.outcome == "resolved":
        alert = db.get(Alert, record.alert_id)
        if alert and alert.status != "resolved":
            alert.status = "resolved"
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by_user_id = current_user.id

    db.commit()
    db.refresh(record)
    return MaintenanceRecordResponse.model_validate(record)
