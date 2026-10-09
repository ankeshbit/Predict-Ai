"""
Demo Fleet Management Endpoints.

PRD FR-11: Demo data seeding and administrative reset.
Deviation §9 (docs/deviations.md): Demo replay simulated stream — admin-only DB-backed
cycle-by-cycle advance of held-out FD001 engines through the live scoring pipeline.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.entities import (
    Dataset,
    Job,
    Machine,
    ModelVersion,
    SensorReading,
    User,
)
from app.services.demo_replay_worker import (
    get_replay_state,
    set_replay_state,
    wake_demo_replay_worker,
)
from app.services.importer import seed_demo_engines

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo Fleet"])


class DemoResetResponse(BaseModel):
    status: str
    message: str
    demo_units: Dict[str, Any]
    cleared_user_datasets_count: int = 0
    cleared_user_machines_count: int = 0


class DemoResetPreviewResponse(BaseModel):
    demo_machines_count: int
    user_datasets_count: int
    user_machines_count: int
    user_readings_count: int


class DemoReplayStatusResponse(BaseModel):
    running: bool
    completed: bool = False
    current_machine_cycles: Dict[str, int]  # machine_code -> current_cycle
    message: str


class DemoReplayStartResponse(BaseModel):
    status: str
    message: str


class DemoReplayStopResponse(BaseModel):
    status: str
    message: str


@router.get(
    "/replay/status",
    response_model=DemoReplayStatusResponse,
    summary="Get demo replay status (Admin only)",
)
def get_replay_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Returns whether the simulated stream replay is running, completed, and per-machine cycle positions."""
    state = get_replay_state(db)
    return DemoReplayStatusResponse(
        running=state.get("running", False),
        completed=state.get("completed", False),
        current_machine_cycles=state.get("machine_cycles", {}),
        message="Demo replay (simulated stream) status.",
    )


@router.post(
    "/replay/start",
    response_model=DemoReplayStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start demo replay simulated stream (Admin only)",
)
def start_replay(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Starts the demo replay stream.
    Sets running=True in the database setting table and returns immediately.
    The background worker advances telemetry cycle-by-cycle and auto-stops at the last cycle.
    """
    state = get_replay_state(db)
    if state.get("running", False):
        return DemoReplayStartResponse(
            status="already_running",
            message="Demo replay stream is already running.",
        )

    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == "cmapss_fd001",
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    if not active_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "NO_ACTIVE_MODEL", "message": "No active failure_risk model registered."}},
        )

    state["running"] = True
    state["completed"] = False
    set_replay_state(db, state)

    # Record DB-backed Job (PRD requirement: DB-backed job for demo replay)
    job = Job(
        job_type="demo_replay",
        status="running",
        input_params={"action": "start"},
        created_by_user_id=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()

    wake_demo_replay_worker()

    return DemoReplayStartResponse(
        status="started",
        message="Demo replay stream started. Background server worker will stream cycles.",
    )


@router.post(
    "/replay/stop",
    response_model=DemoReplayStopResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop demo replay simulated stream (Admin only)",
)
def stop_replay(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Stops the demo replay stream. The last cycle positions are preserved in the DB."""
    state = get_replay_state(db)
    state["running"] = False
    set_replay_state(db, state)

    # Complete DB-backed Job
    active_jobs = db.scalars(
        select(Job).where(Job.job_type == "demo_replay", Job.status == "running")
    ).all()
    for j in active_jobs:
        j.status = "completed"
        j.completed_at = datetime.now(timezone.utc)
    db.commit()

    return DemoReplayStopResponse(
        status="stopped",
        message="Demo replay (simulated stream) has been stopped.",
    )


@router.get(
    "/reset/preview",
    response_model=DemoResetPreviewResponse,
    summary="Preview items that will be affected by demo reset (Admin only)",
)
def preview_demo_reset(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Returns counts of demo machines and user-uploaded datasets/machines that can be cleared."""
    user_ds_count = db.scalar(select(func.count(Dataset.id)).where(Dataset.is_demo.is_(False))) or 0
    user_mach_count = db.scalar(select(func.count(Machine.id)).where(Machine.is_demo.is_(False))) or 0
    user_readings_count = db.scalar(
        select(func.count(SensorReading.id))
        .join(Machine, SensorReading.machine_id == Machine.id)
        .where(Machine.is_demo.is_(False))
    ) or 0
    demo_mach_count = db.scalar(select(func.count(Machine.id)).where(Machine.is_demo.is_(True))) or 3

    return DemoResetPreviewResponse(
        demo_machines_count=demo_mach_count,
        user_datasets_count=user_ds_count,
        user_machines_count=user_mach_count,
        user_readings_count=user_readings_count,
    )


@router.post(
    "/reset",
    response_model=DemoResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset demo fleet to initial seeded state (Admin only)",
)
def reset_demo_fleet(
    clear_user_datasets: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Restores the demo fleet machines (Healthy, Warning, Critical) to their
    held-out initial baseline state and reference scores.
    Clears any demo machine alerts, maintenance actions, or predictions,
    and resets their operational status to 'active'.
    Also stops any running replay stream.
    If clear_user_datasets is True, safely purges all user-uploaded datasets and their machines.
    Strictly restricted to Admin role.
    """
    # Stop any running replay
    set_replay_state(db, {"running": False, "completed": False, "machine_cycles": {}})
    active_jobs = db.scalars(
        select(Job).where(Job.job_type == "demo_replay", Job.status == "running")
    ).all()
    for j in active_jobs:
        j.status = "completed"
        j.completed_at = datetime.now(timezone.utc)
    db.commit()

    from app.core.rate_limit import reset_all_limiters
    reset_all_limiters()

    cleared_ds = 0
    cleared_mach = 0
    if clear_user_datasets:
        # Purge user-uploaded machines and related entities
        user_machines = db.scalars(select(Machine).where(Machine.is_demo.is_(False))).all()
        cleared_mach = len(user_machines)
        for m in user_machines:
            db.delete(m)
        db.flush()

        user_datasets = db.scalars(select(Dataset).where(Dataset.is_demo.is_(False))).all()
        cleared_ds = len(user_datasets)
        for ds in user_datasets:
            db.delete(ds)
        db.commit()

    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == "cmapss_fd001",
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    if not active_model:
        from app.core.errors import BadRequestError
        raise BadRequestError(
            code="NO_ACTIVE_MODEL",
            message="No active failure_risk model found to reset demo fleet from.",
        )

    bundle_path = Path(active_model.artifact_path)
    if not bundle_path.exists() or not (bundle_path / "demo" / "demo_units.csv").exists():
        from app.core.errors import BadRequestError
        raise BadRequestError(
            code="BUNDLE_DATA_MISSING",
            message=f"Demo artifacts not found at {active_model.artifact_path}",
        )

    try:
        results = seed_demo_engines(bundle_path, session=db)
    except Exception as exc:
        logger.error("Demo reset failed: %s", exc, exc_info=True)
        from app.core.errors import InternalServerError
        raise InternalServerError(
            code="DEMO_RESET_FAILED",
            message=f"Failed to reset demo fleet: {str(exc)}",
        )

    return DemoResetResponse(
        status="success",
        message="Demo fleet reset successfully to initial baseline."
        + (f" Cleared {cleared_ds} user dataset(s) and {cleared_mach} machine(s)." if clear_user_datasets else ""),
        demo_units=results,
        cleared_user_datasets_count=cleared_ds,
        cleared_user_machines_count=cleared_mach,
    )
