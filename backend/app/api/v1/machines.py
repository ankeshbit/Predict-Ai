"""
Machines API router: fleet listing, machine details, and telemetry history with server-side downsampling.
"""

import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models.entities import (
    Alert,
    Anomaly,
    Dataset,
    Machine,
    MaintenanceRecord,
    ModelVersion,
    Prediction,
    SensorReading,
    User,
)
from app.schemas.machines import (
    MachineArchiveRequest,
    MachineCreateRequest,
    MachineListResponse,
    MachineResponse,
    MachineTimelineItem,
    MachineTimelineResponse,
    MachineUpdateRequest,
    SensorCycleReading,
    SensorHistoryResponse,
)
from app.schemas.predictions import (
    AdditiveBreakdownResponse,
    PredictionLineageResponse,
    PredictionListResponse,
    PredictionResponse,
)
from app.services.scoring_service import score_machine_trajectory

router = APIRouter(prefix="/machines", tags=["Machines"])


def _enrich_machine_response(machine: Machine, db: Session) -> Dict[str, Any]:
    """Fetch latest prediction for a machine and return enrichment fields."""
    latest_pred = db.scalar(
        select(Prediction)
        .where(Prediction.machine_id == machine.id)
        .order_by(Prediction.cycle.desc())
        .limit(1)
    )
    latest_reading_cycle = db.scalar(
        select(SensorReading.cycle_index)
        .where(SensorReading.machine_id == machine.id)
        .order_by(SensorReading.cycle_index.desc())
        .limit(1)
    )

    if latest_pred is None:
        return {"current_cycle": latest_reading_cycle} if latest_reading_cycle is not None else {}

    resolved_cycle = max(c for c in [latest_pred.cycle, latest_reading_cycle] if c is not None)

    # Determine reliability_status from flags
    dq = latest_pred.reliability_flags.get("data_quality", "DATA_OK") if latest_pred.reliability_flags else "DATA_OK"
    reliability_status = "ok" if dq == "DATA_OK" else "reduced"
    # Anomaly severity = penalty_anomaly / 100 (normalised 0-1)
    anomaly_severity = min(1.0, latest_pred.penalty_anomaly / 100.0)

    latest_anom = db.scalar(
        select(Anomaly)
        .where(Anomaly.machine_id == machine.id)
        .order_by(Anomaly.cycle.desc())
        .limit(1)
    )
    anom_threshold = None
    active_anom_model = db.scalar(
        select(ModelVersion).where(ModelVersion.task == "anomaly", ModelVersion.is_active.is_(True))
    )
    if active_anom_model and active_anom_model.decision_threshold is not None:
        anom_threshold = active_anom_model.decision_threshold

    latest_alert = db.scalar(
        select(Alert)
        .where(Alert.machine_id == machine.id)
        .order_by(Alert.created_at.desc())
        .limit(1)
    )

    dataset_name = None
    if machine.dataset_id:
        ds = db.get(Dataset, machine.dataset_id)
        if ds:
            dataset_name = ds.name

    return {
        "dataset_name": dataset_name,
        "failure_probability": latest_pred.failure_probability,
        "risk_level": latest_pred.risk_level,
        "current_cycle": resolved_cycle,
        "anomaly_score": latest_pred.penalty_anomaly / 100.0,
        "anomaly_severity": anomaly_severity,
        "is_anomaly": latest_anom.is_anomaly if latest_anom is not None else None,
        "anomaly_threshold": anom_threshold,
        "reliability_status": reliability_status,
        "prediction_horizon": latest_pred.horizon,
        "prediction_horizon_unit": latest_pred.horizon_unit,
        "schema_mapping_hash": latest_pred.schema_mapping_hash,
        "feature_config_version": latest_pred.feature_config_version,
        "preprocessing_version": latest_pred.preprocessing_version,
        "failure_model_version_id": str(latest_pred.failure_model_version_id),
        "anomaly_model_version_id": str(latest_pred.anomaly_model_version_id) if latest_pred.anomaly_model_version_id else None,
        "penalty_risk": latest_pred.penalty_risk,
        "penalty_anomaly": latest_pred.penalty_anomaly,
        "penalty_dq": latest_pred.penalty_dq,
        "penalty_trend": latest_pred.penalty_trend,
        "rule_id": latest_alert.recommendation_rule_id if latest_alert else None,
        "recommendation_text": latest_alert.recommendation_text if latest_alert else None,
    }


def _machine_to_response(machine: Machine, db: Session) -> MachineResponse:
    """Build MachineResponse enriched with latest prediction."""
    base = MachineResponse.model_validate(machine)
    enrichment = _enrich_machine_response(machine, db)
    return base.model_copy(update=enrichment)


@router.get("", response_model=MachineListResponse)
def list_machines(
    operational_status: Optional[str] = Query(None, description="Filter by operational status"),
    health_band: Optional[str] = Query(None, description="Filter by health band"),
    is_demo: Optional[bool] = Query(None, description="Filter by demo machine flag"),
    search: Optional[str] = Query(None, description="Search machine code"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists machines in the fleet with filtering and pagination."""
    stmt = select(Machine)

    if operational_status:
        stmt = stmt.where(Machine.operational_status == operational_status)
    if health_band:
        stmt = stmt.where(Machine.health_band == health_band)
    if is_demo is not None:
        stmt = stmt.where(Machine.is_demo == is_demo)
    if search:
        stmt = stmt.where(Machine.machine_code.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Machine.machine_code).offset(offset).limit(limit)).all()

    return MachineListResponse(
        items=[_machine_to_response(m, db) for m in items],
        total=total,
    )


@router.post("", response_model=MachineResponse, status_code=201)
def create_machine(
    payload: MachineCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Creates a new machine in the fleet (Admin only)."""
    existing = db.scalar(select(Machine).where(Machine.machine_code == payload.machine_code))
    if existing:
        raise ConflictError(message=f"Machine with code {payload.machine_code} already exists")

    machine = Machine(
        id=uuid.uuid4(),
        machine_code=payload.machine_code,
        name=payload.name,
        machine_type=payload.machine_type or "Turbofan Engine",
        location=payload.location,
        notes=payload.notes,
        install_date=payload.install_date,
        dataset_id=payload.dataset_id,
        source_unit_id=payload.source_unit_id,
        operational_status="active",
    )
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return MachineResponse.model_validate(machine)


@router.get("/{machine_id}", response_model=MachineResponse)
def get_machine(
    machine_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves detailed operational status and health metrics for a specific machine."""
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine with id {machine_id} not found")
    return _machine_to_response(machine, db)


@router.patch("/{machine_id}", response_model=MachineResponse)
def update_machine(
    machine_id: uuid.UUID,
    payload: MachineUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Partially updates machine metadata (name, machine_type, location, notes).
    Conforms to PRD §14.2 & ADR: operational status can only change via maintenance workflow.
    """
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine with id {machine_id} not found")

    if payload.name is not None:
        machine.name = payload.name
    if payload.machine_type is not None:
        machine.machine_type = payload.machine_type
    if payload.location is not None:
        machine.location = payload.location
    if payload.notes is not None:
        machine.notes = payload.notes

    db.commit()
    db.refresh(machine)
    return _machine_to_response(machine, db)


@router.post("/{machine_id}/archive", response_model=MachineResponse)
def archive_machine(
    machine_id: uuid.UUID,
    payload: MachineArchiveRequest = MachineArchiveRequest(),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Archives a machine (Admin only).
    Blocks if machine has open alerts unless force=True (PRD §14.2).
    """
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine with id {machine_id} not found")

    open_alerts_count = db.scalar(
        select(func.count()).select_from(
            select(Alert).where(
                Alert.machine_id == machine_id,
                Alert.status.in_(["open", "acknowledged"]),
            ).subquery()
        )
    ) or 0

    if open_alerts_count > 0 and not payload.force:
        raise ConflictError(
            code="OPEN_ALERTS_EXIST",
            message=f"Machine has {open_alerts_count} open alerts. Provide force=true to archive.",
        )

    machine.operational_status = "archived"
    db.commit()
    db.refresh(machine)
    return _machine_to_response(machine, db)


@router.get("/{machine_id}/timeline", response_model=MachineTimelineResponse)
def get_machine_timeline(
    machine_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """
    Returns a unified timeline of anomalies, alerts, and maintenance events for a machine (PRD §14.2).
    """
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine with id {machine_id} not found")

    timeline_items: List[MachineTimelineItem] = []

    # 1. Anomalies
    anomalies = db.scalars(
        select(Anomaly).where(Anomaly.machine_id == machine_id).order_by(Anomaly.cycle.desc())
    ).all()
    for a in anomalies:
        timeline_items.append(
            MachineTimelineItem(
                id=a.id,
                event_type="anomaly",
                cycle=a.cycle,
                timestamp=a.detected_at,
                title=f"Anomaly detected at cycle {a.cycle} (score {a.anomaly_score:.2f})",
                severity=a.severity,
                status="flagged" if a.is_anomaly else "nominal",
                details={"score": a.anomaly_score, "is_anomaly": a.is_anomaly},
            )
        )

    # 2. Alerts
    alerts = db.scalars(
        select(Alert).where(Alert.machine_id == machine_id).order_by(Alert.trigger_cycle.desc())
    ).all()
    for al in alerts:
        timeline_items.append(
            MachineTimelineItem(
                id=al.id,
                event_type="alert",
                cycle=al.trigger_cycle,
                timestamp=al.created_at,
                title=f"Alert: {al.alert_type.replace('_', ' ').title()}",
                severity=al.severity,
                status=al.status,
                details={
                    "alert_type": al.alert_type,
                    "trigger_score": al.trigger_score,
                    "recommendation": al.recommendation_text,
                },
            )
        )

    # 3. Maintenance records
    m_records = db.scalars(
        select(MaintenanceRecord).where(MaintenanceRecord.machine_id == machine_id).order_by(MaintenanceRecord.started_at.desc())
    ).all()
    for m in m_records:
        timeline_items.append(
            MachineTimelineItem(
                id=m.id,
                event_type="maintenance",
                cycle=None,
                timestamp=m.started_at,
                title=f"Maintenance: {m.issue or m.action_type}",
                severity=None,
                status=m.status,
                details={
                    "decision": m.decision,
                    "action_taken": m.action_taken,
                    "outcome": m.outcome,
                },
            )
        )

    # Sort descending by timestamp
    timeline_items.sort(key=lambda item: item.timestamp, reverse=True)

    return MachineTimelineResponse(
        machine_id=machine.id,
        machine_code=machine.machine_code,
        total_events=len(timeline_items),
        events=timeline_items,
    )




@router.get("/{machine_id}/sensors", response_model=SensorHistoryResponse)
def get_sensor_history(
    machine_id: uuid.UUID,
    from_cycle: Optional[int] = Query(None, ge=1, description="Start cycle inclusive"),
    to_cycle: Optional[int] = Query(None, ge=1, description="End cycle inclusive"),
    downsample_to: Optional[int] = Query(None, ge=10, le=500, description="Max points to return using uniform stride"),
    channels: Optional[str] = Query(None, description="Comma-separated sensor names (e.g. sensor_2,sensor_3)"),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """
    Returns time-series sensor history for a machine.
    Supports server-side downsampling for performant browser rendering.
    """
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine with id {machine_id} not found")

    stmt = select(SensorReading).where(SensorReading.machine_id == machine_id)
    if from_cycle:
        stmt = stmt.where(SensorReading.cycle >= from_cycle)
    if to_cycle:
        stmt = stmt.where(SensorReading.cycle <= to_cycle)

    raw_readings = db.scalars(stmt.order_by(SensorReading.cycle.asc())).all()
    total_cycles = len(raw_readings)

    # Server-side uniform downsampling if requested and dataset exceeds target
    if downsample_to and total_cycles > downsample_to:
        indices = np.unique(np.linspace(0, total_cycles - 1, downsample_to, dtype=int))
        sampled_readings = [raw_readings[i] for i in indices]
    else:
        sampled_readings = raw_readings

    # Filter channel columns if requested
    requested_channels = [c.strip() for c in channels.split(",")] if channels else None

    results: List[SensorCycleReading] = []
    for r in sampled_readings:
        sensor_dict = {}
        for s_idx in range(1, 22):
            s_name = f"sensor_{s_idx}"
            if requested_channels is None or s_name in requested_channels:
                sensor_dict[s_name] = getattr(r, s_name, None)

        results.append(
            SensorCycleReading(
                cycle=r.cycle,
                recorded_at=r.recorded_at,
                op_setting_1=r.op_setting_1,
                op_setting_2=r.op_setting_2,
                op_setting_3=r.op_setting_3,
                sensors=sensor_dict,
                imputed_fields=r.imputed_fields,
            )
        )

    return SensorHistoryResponse(
        machine_id=machine.id,
        machine_code=machine.machine_code,
        total_cycles=total_cycles,
        returned_cycles=len(results),
        readings=results,
    )


@router.get("/{machine_id}/predictions", response_model=PredictionListResponse)
def get_machine_predictions(
    machine_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves recent scored predictions and additive health breakdown points for a machine."""
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine {machine_id} not found")

    preds = db.scalars(
        select(Prediction)
        .where(Prediction.machine_id == machine_id)
        .order_by(Prediction.cycle.desc())
        .limit(limit)
    ).all()

    items = []
    for p in preds:
        lineage = PredictionLineageResponse(
            dataset_version=p.dataset_version,
            schema_mapping_hash=p.schema_mapping_hash,
            feature_config_version=p.feature_config_version,
            preprocessing_version=p.preprocessing_version,
            failure_model_version_id=p.failure_model_version_id,
            anomaly_model_version_id=p.anomaly_model_version_id,
            health_config_id=p.health_config_id,
            horizon=p.horizon,
            horizon_unit=p.horizon_unit,
            as_of_index=p.as_of_index,
            predicted_at=p.predicted_at,
            input_window_start=p.input_window_start,
            input_window_end=p.input_window_end,
        )
        breakdown = AdditiveBreakdownResponse(
            start=100.0,
            failure_risk_points=p.penalty_risk,
            anomaly_points=p.penalty_anomaly,
            data_quality_points=p.penalty_dq,
            trend_points=None,
            trend_status="not_enabled",
            clipping_adjustment_points=p.clipping_adjustment,
            health_indicator=p.health_indicator,
        )
        items.append(
            PredictionResponse(
                id=p.id,
                machine_id=p.machine_id,
                cycle=p.cycle,
                as_of_index=p.as_of_index,
                predicted_at=p.predicted_at,
                failure_probability=p.failure_probability,
                risk_level=p.risk_level,
                health_indicator=p.health_indicator,
                health_band=p.health_band,
                penalty_risk=p.penalty_risk,
                penalty_anomaly=p.penalty_anomaly,
                penalty_dq=p.penalty_dq,
                penalty_trend=p.penalty_trend,
                clipping_adjustment=p.clipping_adjustment,
                breakdown=breakdown,
                lineage=lineage,
                reliability_flags=p.reliability_flags,
            )
        )

    return PredictionListResponse(items=items, total=len(items))


@router.post("/{machine_id}/score")
def score_machine(
    machine_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Scores sensor readings for a machine using the registered active model bundle."""
    return score_machine_trajectory(machine_id, db)

