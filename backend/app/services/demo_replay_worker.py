"""
Demo Replay Background Worker.

PRD FR-11 & Deviation §9:
Simulated live stream worker that advances held-out demo engines cycle-by-cycle
through the live scoring pipeline, evaluates alert rules, and halts automatically
at the end of the trajectory.

Key Guarantees:
1. Single-worker execution across multiple backend instances via PostgreSQL advisory lock.
2. State persisted in settings table (key="demo_replay"), surviving backend restarts.
3. Configurable tick interval via settings.DEMO_REPLAY_INTERVAL_SECONDS (default 5s).
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.models.entities import Job, Machine, ModelVersion, SensorReading, Setting
from app.services.scoring_service import score_machine_trajectory

logger = logging.getLogger(__name__)

DEMO_REPLAY_SETTING_KEY = "demo_replay"
# Unique 64-bit integer for PostgreSQL advisory lock
DEMO_REPLAY_ADVISORY_LOCK_ID = 84729104


def get_replay_state(db: Session) -> Dict[str, Any]:
    setting = db.scalar(select(Setting).where(Setting.key == DEMO_REPLAY_SETTING_KEY))
    if setting is None:
        return {"running": False, "completed": False, "machine_cycles": {}}
    return dict(setting.value)


def set_replay_state(db: Session, state: Dict[str, Any], commit: bool = True) -> None:
    setting = db.scalar(select(Setting).where(Setting.key == DEMO_REPLAY_SETTING_KEY))
    if setting is None:
        setting = Setting(
            key=DEMO_REPLAY_SETTING_KEY,
            value=dict(state),
            description="Demo replay (simulated stream) state — admin-only",
        )
        db.add(setting)
    else:
        setting.value = dict(state)
        flag_modified(setting, "value")
    if commit:
        db.commit()
    else:
        db.flush()


def advance_replay_tick(db: Session, commit: bool = True) -> bool:
    """
    Executes a single cycle advancement tick for all active demo engines.
    Returns True if at least one engine advanced, or False if replay is stopped / completed.
    """
    state = get_replay_state(db)
    if not state.get("running", False):
        return False
    if state.get("completed", False):
        return False

    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == "cmapss_fd001",
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    if not active_model:
        logger.warning("Demo replay tick skipped: No active failure_risk model registered.")
        return False

    bundle_path = Path(active_model.artifact_path)
    demo_units_path = bundle_path / "demo" / "demo_units.csv"
    if not demo_units_path.is_file():
        logger.warning("Demo replay tick skipped: Missing demo_units.csv at %s", demo_units_path)
        return False

    demo_machines = db.scalars(
        select(Machine).where(Machine.is_demo.is_(True), Machine.operational_status == "active")
    ).all()
    if not demo_machines:
        logger.warning("Demo replay tick skipped: No active demo machines in fleet.")
        return False

    units_df = pd.read_csv(demo_units_path)
    unit_col_units = "unit_id" if "unit_id" in units_df.columns else "machine_id"
    cycle_col = "cycle" if "cycle" in units_df.columns else "cycle_index"

    machine_cycles = dict(state.get("machine_cycles", {}))
    any_advanced = False

    for machine in demo_machines:
        if machine.source_unit_id is None:
            continue

        u_id = machine.source_unit_id
        engine_rows = units_df[units_df[unit_col_units] == u_id].sort_values(cycle_col)
        if engine_rows.empty:
            continue

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
            # Engine reached end of its trajectory
            machine_cycles[machine.machine_code] = current_max
            continue

        next_row = next_cycle_rows.iloc[0]
        next_cycle = int(next_row[cycle_col])

        # Idempotency guard: skip if cycle already inserted concurrently
        already_exists = db.scalar(
            select(SensorReading.id).where(
                SensorReading.machine_id == machine.id,
                SensorReading.cycle_index == next_cycle,
            )
        )
        if already_exists:
            machine_cycles[machine.machine_code] = next_cycle
            continue

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

        # Re-score trajectory for this machine through live scoring service
        try:
            score_machine_trajectory(machine.id, db, commit=commit)
        except Exception as exc:
            logger.warning("Replay scoring failed for %s: %s", machine.machine_code, exc)
        machine_cycles[machine.machine_code] = next_cycle
        any_advanced = True

    if any_advanced:
        latest_state = get_replay_state(db)
        state["running"] = bool(latest_state.get("running", False))
        state["completed"] = False
        state["machine_cycles"] = machine_cycles
        state["last_advanced_at"] = datetime.now(timezone.utc).isoformat()
        set_replay_state(db, state, commit=commit)
        logger.info("Demo replay tick advanced cycles: %s", machine_cycles)
        return True
    else:
        # All demo engines reached the end of their trajectory
        logger.info("Demo replay stream completed: all engine trajectories reached the last cycle.")
        state["running"] = False
        state["completed"] = True
        state["machine_cycles"] = machine_cycles
        set_replay_state(db, state, commit=commit)

        # Complete running Jobs
        active_jobs = db.scalars(
            select(Job).where(Job.job_type == "demo_replay", Job.status == "running")
        ).all()
        for j in active_jobs:
            j.status = "completed"
            j.completed_at = datetime.now(timezone.utc)
        if commit:
            db.commit()
        else:
            db.flush()
        return False


def run_tick_with_advisory_lock() -> bool:
    """
    Executes a single tick protected by a PostgreSQL transaction-scoped advisory lock
    (pg_try_advisory_xact_lock) taken inside the same transaction that performs the tick.

    Why pg_try_advisory_xact_lock:
    1. Works reliably through Neon's PgBouncer (transaction pooling) where session locks
       can bleed across pooled connections or fail to unlock.
    2. Automatically released by PostgreSQL when the transaction commits or rolls back,
       preventing stale or leaking locks.
    """
    from app.core.db import SessionLocal

    with SessionLocal() as db:
        is_postgres = False
        try:
            is_postgres = db.bind is not None and db.bind.dialect.name == "postgresql"
        except Exception:
            pass

        if is_postgres:
            try:
                locked = db.scalar(
                    text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                    {"lock_id": DEMO_REPLAY_ADVISORY_LOCK_ID},
                )
                if not locked:
                    # Another server worker instance currently holds the transaction lock
                    db.rollback()
                    return False
            except Exception as exc:
                logger.warning("Transaction advisory lock acquisition failed: %s", exc)
                db.rollback()
                return False

        try:
            result = advance_replay_tick(db, commit=False)
            db.commit()
            return result
        except Exception:
            db.rollback()
            raise


_worker_wake_event: Optional[asyncio.Event] = None
_worker_loop: Optional[asyncio.AbstractEventLoop] = None


def wake_demo_replay_worker() -> None:
    """Signals the background replay worker to immediately wake from idle sleep."""
    global _worker_wake_event, _worker_loop
    if _worker_wake_event is not None and _worker_loop is not None and not _worker_loop.is_closed():
        try:
            _worker_loop.call_soon_threadsafe(_worker_wake_event.set)
        except Exception:
            pass


def is_replay_running() -> bool:
    """Checks whether demo replay is active without acquiring the advisory lock."""
    from app.core.db import SessionLocal
    try:
        with SessionLocal() as db:
            state = get_replay_state(db)
            return bool(state.get("running", False) and not state.get("completed", False))
    except Exception as exc:
        logger.warning("Failed to check replay state: %s", exc)
        return False


async def demo_replay_worker_loop():
    """
    Background asyncio worker task executing periodically.

    Neon Scale-to-Zero Optimization:
    - While running: ticks every DEMO_REPLAY_INTERVAL_SECONDS (default 5s).
    - While stopped / idle: checks settings table only every
      DEMO_REPLAY_IDLE_INTERVAL_SECONDS (default 30s) or immediately when
      woken by wake_demo_replay_worker() upon an admin start request.
      This minimizes database wakeups and allows Neon compute to auto-suspend.
    """
    global _worker_wake_event, _worker_loop
    logger.info("Demo replay background worker loop started.")
    _worker_loop = asyncio.get_running_loop()
    _worker_wake_event = asyncio.Event()

    try:
        while True:
            is_running = False
            try:
                is_running = await asyncio.to_thread(is_replay_running)
                if is_running:
                    await asyncio.to_thread(run_tick_with_advisory_lock)
                    is_running = await asyncio.to_thread(is_replay_running)
            except asyncio.CancelledError:
                logger.info("Demo replay worker task cancelled.")
                break
            except Exception as exc:
                logger.exception("Unexpected error in demo replay worker loop: %s", exc)

            try:
                if is_running:
                    interval = max(0.1, float(settings.DEMO_REPLAY_INTERVAL_SECONDS))
                else:
                    interval = max(0.1, float(settings.DEMO_REPLAY_IDLE_INTERVAL_SECONDS))

                _worker_wake_event.clear()
                try:
                    await asyncio.wait_for(_worker_wake_event.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    pass
            except asyncio.CancelledError:
                break
    finally:
        _worker_wake_event = None
        _worker_loop = None

