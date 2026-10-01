"""
Machines API router: fleet listing, machine details, and telemetry history with server-side downsampling.
"""

import uuid
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import Machine, Prediction, SensorReading, User
from app.schemas.machines import (
    MachineListResponse,
    MachineResponse,
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
        items=[MachineResponse.model_validate(m) for m in items],
        total=total,
    )


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
    return MachineResponse.model_validate(machine)




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

