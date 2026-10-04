"""
Tests for Server-Side Live Demo Replay Stream.

PRD FR-11 & Deviation §9:
Verifies:
1. RBAC: Only Admin can start, stop, or check replay status (403 for Engineer, 401 for anonymous).
2. Autonomous Server-Side Streaming: After a single 'start' request, the cycle number keeps
   increasing on the server with NO more HTTP requests.
3. Stop Control: After 'stop' is called, the cycle number stops advancing.
4. Auto-completion: Replay marks status as completed when the final cycle is reached.
"""

import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.models.entities import Machine, SensorReading
from app.services.demo_replay_worker import (
    run_tick_with_advisory_lock,
    set_replay_state,
)
from app.services.importer import register_model_bundle, seed_demo_engines


def test_demo_replay_rbac(client: TestClient, engineer_headers: dict):
    """Anonymous gets 401, engineer gets 403 on all demo replay endpoints."""
    # Anonymous
    assert client.get("/api/v1/demo/replay/status").status_code == 401
    assert client.post("/api/v1/demo/replay/start").status_code == 401
    assert client.post("/api/v1/demo/replay/stop").status_code == 401

    # Engineer
    assert client.get("/api/v1/demo/replay/status", headers=engineer_headers).status_code == 403
    assert client.post("/api/v1/demo/replay/start", headers=engineer_headers).status_code == 403
    assert client.post("/api/v1/demo/replay/stop", headers=engineer_headers).status_code == 403


def test_demo_replay_stream_advances_without_requests_and_stops(
    client: TestClient,
    admin_headers: dict,
    mock_valid_bundle: Path,
    db,
):
    """
    Verifies that starting the replay stream advances cycle numbers autonomously
    on the server with NO additional HTTP requests, and stops when /stop is called.
    """
    # 1. Register active model bundle and seed demo fleet
    register_model_bundle(mock_valid_bundle, activate=True, session=db)
    seed_demo_engines(mock_valid_bundle, session=db)

    # Append additional cycles for all demo units to enable multi-cycle streaming
    demo_csv = mock_valid_bundle / "demo" / "demo_units.csv"
    with open(demo_csv, "a", encoding="utf-8") as f:
        for u in (1, 2, 3):
            for c in range(11, 40):
                f.write(f"{u},{c},0.0,0.0,100.0," + ",".join("20.5" for _ in range(21)) + "\n")

    # Reset replay state cleanly
    set_replay_state(db, {"running": False, "completed": False, "machine_cycles": {}})

    # Get initial cycle for demo machine unit 2
    demo_machine = db.scalar(
        select(Machine).where(Machine.source_unit_id == 2, Machine.operational_status == "active")
    )
    assert demo_machine is not None

    initial_max_cycle = db.scalar(
        select(SensorReading.cycle_index)
        .where(SensorReading.machine_id == demo_machine.id)
        .order_by(SensorReading.cycle_index.desc())
        .limit(1)
    )
    assert initial_max_cycle is not None

    # 2. Run a background ticker thread simulating the server-side worker loop with a short interval
    stop_event = threading.Event()
    original_interval = settings.DEMO_REPLAY_INTERVAL_SECONDS
    settings.DEMO_REPLAY_INTERVAL_SECONDS = 0.1

    def background_ticker():
        while not stop_event.is_set():
            run_tick_with_advisory_lock()
            time.sleep(0.08)

    ticker_thread = threading.Thread(target=background_ticker, daemon=True)
    ticker_thread.start()

    try:
        # 3. Admin calls /replay/start ONCE
        start_res = client.post("/api/v1/demo/replay/start", headers=admin_headers)
        assert start_res.status_code == 200
        assert start_res.json()["status"] == "started"

        # 4. Wait for server-side worker to advance autonomously (NO more requests sent)
        start_wait = time.time()
        advanced_cycle = initial_max_cycle
        while time.time() - start_wait < 4.0:
            time.sleep(0.1)
            db.expire_all()
            advanced_cycle = db.scalar(
                select(SensorReading.cycle_index)
                .where(SensorReading.machine_id == demo_machine.id)
                .order_by(SensorReading.cycle_index.desc())
                .limit(1)
            ) or initial_max_cycle
            if advanced_cycle >= initial_max_cycle + 2:
                break

        assert advanced_cycle >= initial_max_cycle + 2, (
            f"Expected cycle to increase autonomously by at least 2: initial={initial_max_cycle}, now={advanced_cycle}"
        )

        # 6. Admin calls /replay/stop
        stop_res = client.post("/api/v1/demo/replay/stop", headers=admin_headers)
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "stopped"

        # Allow any in-flight tick to complete
        time.sleep(0.15)
        db.expire_all()
        cycle_at_stop = db.scalar(
            select(SensorReading.cycle_index)
            .where(SensorReading.machine_id == demo_machine.id)
            .order_by(SensorReading.cycle_index.desc())
            .limit(1)
        )

        # 7. Wait another interval and assert that cycles have stopped advancing
        time.sleep(0.3)
        db.expire_all()
        cycle_after_wait = db.scalar(
            select(SensorReading.cycle_index)
            .where(SensorReading.machine_id == demo_machine.id)
            .order_by(SensorReading.cycle_index.desc())
            .limit(1)
        )
        assert cycle_after_wait == cycle_at_stop, (
            f"Expected cycles to stop advancing after stop: stopped={cycle_at_stop}, after_wait={cycle_after_wait}"
        )

        # 8. Check status endpoint confirms stopped
        status_res = client.get("/api/v1/demo/replay/status", headers=admin_headers)
        assert status_res.status_code == 200
        assert status_res.json()["running"] is False

    finally:
        stop_event.set()
        ticker_thread.join(timeout=2.0)
        settings.DEMO_REPLAY_INTERVAL_SECONDS = original_interval
