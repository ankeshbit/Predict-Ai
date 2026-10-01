"""
Tests for Demo Fleet Management & Reset API (POST /api/v1/demo/reset).

Validates PRD FR-11:
- Role enforcement: Admin allowed, Engineer forbidden (403), Unauthenticated (401)
- Demo fleet reset restoration of Healthy, Warning, Critical engines
- Reset side-effects: removes old alerts and maintenance records, resets status to 'active'
- Robust error handling when active model or artifacts are missing
"""

import uuid
from fastapi.testclient import TestClient

from app.models.entities import Alert, Machine, MaintenanceRecord, ModelVersion, User
from app.services.importer import register_model_bundle, seed_demo_engines


def test_demo_reset_requires_auth(client: TestClient):
    """Anonymous requests must be rejected with 401."""
    resp = client.post("/api/v1/demo/reset")
    assert resp.status_code == 401


def test_demo_reset_forbidden_for_engineer(client: TestClient, engineer_headers: dict):
    """Engineers cannot trigger demo reset (403 Forbidden)."""
    resp = client.post(
        "/api/v1/demo/reset",
        headers=engineer_headers,
    )
    assert resp.status_code == 403


def test_demo_reset_fails_without_active_model(client: TestClient, admin_headers: dict, db):
    """Reset fails with 400 if no active model exists."""
    # Ensure no active model
    db.query(ModelVersion).update({ModelVersion.is_active: False})
    db.commit()

    resp = client.post(
        "/api/v1/demo/reset",
        headers=admin_headers,
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "NO_ACTIVE_MODEL"


def test_demo_reset_success_and_side_effects(client: TestClient, admin_headers: dict, mock_valid_bundle, db):
    """Admin resets demo fleet: restores machines, clears alerts, resets maintenance status."""
    # 1. Register and seed initial demo
    register_model_bundle(mock_valid_bundle, activate=True, session=db)
    seed_demo_engines(mock_valid_bundle, session=db)

    # 2. Modify one demo machine to have 'maintenance' status and an open alert
    warning_machine = db.query(Machine).filter(Machine.machine_code == "ENGINE-002").first()
    assert warning_machine is not None
    warning_machine.operational_status = "maintenance"

    admin_user = db.query(User).filter(User.role == "admin").first()
    assert admin_user is not None

    alert = Alert(
        id=uuid.uuid4(),
        machine_id=warning_machine.id,
        alert_type="risk_threshold",
        severity="critical",
        status="open",
        trigger_cycle=50,
        trigger_score=0.85,
        recommendation_text="URGENT: Review engine telemetry",
        recommendation_rule_id="RULE-HIGH-RISK",
    )
    db.add(alert)

    maint = MaintenanceRecord(
        id=uuid.uuid4(),
        machine_id=warning_machine.id,
        performed_by_user_id=admin_user.id,
        action_type="inspection",
        status="in_progress",
        issue="Sensor drift detected",
    )
    db.add(maint)
    db.commit()

    # Verify pre-reset state
    assert db.query(Alert).filter(Alert.machine_id == warning_machine.id).count() == 1
    assert db.query(MaintenanceRecord).filter(MaintenanceRecord.machine_id == warning_machine.id).count() == 1
    assert warning_machine.operational_status == "maintenance"

    # 3. Call POST /api/v1/demo/reset as Admin
    resp = client.post(
        "/api/v1/demo/reset",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert "healthy" in res_data["demo_units"]
    assert "warning" in res_data["demo_units"]
    assert "critical" in res_data["demo_units"]

    # 4. Verify post-reset database state
    db.expire_all()
    reloaded_warning = db.query(Machine).filter(Machine.machine_code == "ENGINE-002").first()
    assert reloaded_warning.operational_status == "active"
    assert db.query(Alert).filter(Alert.machine_id == warning_machine.id).count() == 0
    assert db.query(MaintenanceRecord).filter(MaintenanceRecord.machine_id == warning_machine.id).count() == 0
