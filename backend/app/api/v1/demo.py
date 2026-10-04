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
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.entities import Job, Machine, ModelVersion, SensorReading, Setting, User
from app.services.importer import seed_demo_engines

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo Fleet"])


class DemoResetResponse(BaseModel):
    status: str
    message: str
    demo_units: Dict[str, Any]


class DemoReplayStatusResponse(BaseModel):
    running: bool
    current_machine_cycles: Dict[str, int]  # machine_code -> current_cycle
    message: str


class DemoReplayStartResponse(BaseModel):
    status: str
    message: str


class DemoReplayStopResponse(BaseModel):
    status: str
    message: str


_REPLAY_SETTING_KEY = "demo_replay"


def _get_replay_state(db: Session) -> Dict[str, Any]:
    setting = db.scalar(select(Setting).where(Setting.key == _REPLAY_SETTING_KEY))
    if setting is None:
        return {"running": False, "machine_cycles": {}}
    return dict(setting.value)


def _set_replay_state(db: Session, state: Dict[str, Any]) -> None:
    setting = db.scalar(select(Setting).where(Setting.key == _REPLAY_SETTING_KEY))
    if setting is None:
        setting = Setting(
            key=_REPLAY_SETTING_KEY,
            value=state,
            description="Demo replay (simulated stream) state — admin-only",
        )
        db.add(setting)
    else:
        setting.value = state
    db.commit()


@router.get(
    "/replay/status",
    response_model=DemoReplayStatusResponse,
    summary="Get demo replay status (Admin only)",
)
def get_replay_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Returns whether the simulated stream replay is running and per-machine cycle positions."""
    state = _get_replay_state(db)
    return DemoReplayStatusResponse(
        running=state.get("running", False),
        current_machine_cycles=state.get("machine_cycles", {}),
        message="Demo replay (simulated stream) — advances demo engines one cycle at a time through the live pipeline.",
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
    Starts the demo replay: advances each demo machine by one cycle from its current position.

    This endpoint:
    1. Reads the demo machine fleet (is_demo=True).
    2. Finds the next cycle of held-out sensor readings for each demo machine.
    3. Inserts SensorReading rows cycle-by-cycle advancing the machine's current_cycle.
    4. Scores each machine via the registered model bundle.
    5. Evaluates alert rules.
    6. Stores current position in the settings table (key=demo_replay).

    Stops automatically when a machine has reached its last available cycle.
    """
    import pandas as pd

    state = _get_replay_state(db)
    if state.get("running", False):
        return DemoReplayStartResponse(
            status="already_running",
            message="Demo replay is already running. Call /replay/stop to stop it first.",
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

    bundle_path = Path(active_model.artifact_path)
    demo_units_path = bundle_path / "demo" / "demo_units.csv"
    demo_scores_path = bundle_path / "demo" / "demo_reference_scores.csv"

    if not demo_units_path.is_file() or not demo_scores_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "BUNDLE_DATA_MISSING", "message": "Demo artifacts not found in bundle."}},
        )

    units_df = pd.read_csv(demo_units_path)

    unit_col_units = "unit_id" if "unit_id" in units_df.columns else "machine_id"
    cycle_col = "cycle" if "cycle" in units_df.columns else "cycle_index"

    demo_machines = db.scalars(
        select(Machine).where(Machine.is_demo.is_(True), Machine.operational_status == "active")
    ).all()

    if not demo_machines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "NO_DEMO_MACHINES", "message": "No active demo machines in fleet. Run /reset first."}},
        )

    machine_cycles = state.get("machine_cycles", {})
    advanced = {}

    for machine in demo_machines:
        if machine.source_unit_id is None:
            continue

        u_id = machine.source_unit_id
        engine_rows = units_df[units_df[unit_col_units] == u_id].sort_values(cycle_col)

        # Determine current max cycle already in DB for this machine
        current_max = db.scalar(
            select(SensorReading.cycle_index)
            .where(SensorReading.machine_id == machine.id)
            .order_by(SensorReading.cycle_index.desc())
            .limit(1)
        ) or 0

        # Find the next cycle
        next_cycle_rows = engine_rows[engine_rows[cycle_col] > current_max]
        if next_cycle_rows.empty:
            advanced[machine.machine_code] = current_max
            continue  # This engine has reached end of its trajectory

        next_row = next_cycle_rows.iloc[0]
        next_cycle = int(next_row[cycle_col])

        # Insert new SensorReading for the next cycle
        new_reading = SensorReading(
            machine_id=machine.id,
            dataset_id=machine.dataset_id,
            cycle_index=next_cycle,
            op_setting_1=float(next_row["op_setting_1"]) if "op_setting_1" in next_row else None,
            op_setting_2=float(next_row["op_setting_2"]) if "op_setting_2" in next_row else None,
            op_setting_3=float(next_row["op_setting_3"]) if "op_setting_3" in next_row else None,
        )
        for s in range(1, 22):
            col = f"sensor_{s}"
            setattr(new_reading, col, float(next_row[col]) if col in next_row else None)
        db.add(new_reading)
        db.flush()

        # Re-score entire trajectory for this machine (idempotent via scoring_service)
        from app.services.scoring_service import score_machine_trajectory
        try:
            score_machine_trajectory(machine.id, db)
        except Exception as exc:
            logger.warning("Replay score failed for %s: %s", machine.machine_code, exc)

        advanced[machine.machine_code] = next_cycle
        machine_cycles[machine.machine_code] = next_cycle

    new_state = {
        "running": True,
        "machine_cycles": machine_cycles,
    }
    _set_replay_state(db, new_state)

    # Record DB-backed Job (PRD requirement: DB-backed job for demo replay)
    job = Job(
        job_type="demo_replay",
        status="running",
        input_params={"action": "start", "advanced": list(advanced.keys())},
        created_by_user_id=current_user.id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()

    return DemoReplayStartResponse(
        status="advanced",
        message=f"Demo replay advanced. Engines updated: {list(advanced.keys())}",
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
    """Stops the demo replay stream. The last cycle positions are preserved."""
    state = _get_replay_state(db)
    state["running"] = False
    _set_replay_state(db, state)

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
    Also stops any running replay stream.
    Strictly restricted to Admin role.
    """
    # Stop any running replay
    _set_replay_state(db, {"running": False, "machine_cycles": {}})
    active_jobs = db.scalars(
        select(Job).where(Job.job_type == "demo_replay", Job.status == "running")
    ).all()
    for j in active_jobs:
        j.status = "completed"
        j.completed_at = datetime.now(timezone.utc)
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
        message="Demo fleet reset successfully to initial baseline.",
        demo_units=results,
    )
