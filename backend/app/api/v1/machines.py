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
from app.models.entities import Machine, SensorReading, User
from app.schemas.machines import (
    MachineListResponse,
    MachineResponse,
    MachineStatusUpdateRequest,
    SensorCycleReading,
    SensorHistoryResponse,
)

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


@router.patch("/{machine_id}/status", response_model=MachineResponse)
@router.patch("/{machine_id}", response_model=MachineResponse)
def update_machine_status(
    machine_id: uuid.UUID,
    payload: MachineStatusUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Updates operational status of a machine (Admin only)."""
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine with id {machine_id} not found")

    machine.operational_status = payload.operational_status
    db.commit()
    db.refresh(machine)
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
