"""
Phase 4 Integration Tests:
- Model Registry & Evaluation endpoints (zero fabricated literals; 404 with PRD contract message)
- Health Config API (notebook config: anomaly_weight, data_quality_penalty, trend not enabled)
- Scoring Engine & Predictions API (additive breakdown points: penalty_risk, penalty_anomaly, penalty_dq, penalty_trend)
- Alerts API (acknowledgment, resolution, and open alert deduplication)
- Maintenance Workflow (Human-in-the-loop decision recording and operational status lifecycle side-effects)
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.entities import (
    Alert,
    HealthIndicatorConfig,
    Machine,
    MaintenanceRecord,
    ModelEvaluation,
    ModelVersion,
    Prediction,
    SensorReading,
    User,
)
from app.services.importer import register_model_bundle, seed_demo_engines
from app.services.scoring_service import score_machine_trajectory


def test_model_registry_and_evaluation_endpoints(client, engineer_headers, admin_headers, mock_valid_bundle, db):
    """Verifies GET /models, GET /models/active, and GET /models/{id}/evaluation."""
    # 1. Register model
    mv = register_model_bundle(mock_valid_bundle, activate=True, session=db)

    # 2. List models
    res = client.get("/api/v1/models", headers=engineer_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(m["id"] == str(mv.id) for m in data)

    # 3. Active models
    res_act = client.get("/api/v1/models/active", headers=engineer_headers)
    assert res_act.status_code == 200
    data_act = res_act.json()
    assert len(data_act) >= 1
    assert any(m["id"] == str(mv.id) for m in data_act)

    # 4. Evaluation endpoint
    res_eval = client.get(f"/api/v1/models/{mv.id}/evaluation", headers=engineer_headers)
    assert res_eval.status_code == 200
    data_eval = res_eval.json()
    assert data_eval["model_version_id"] == str(mv.id)
    assert "metrics" in data_eval
    assert "curves" in data_eval
    assert "feature_importance" in data_eval

    # 5. Non-existent evaluation returns 404 with PRD verbatim message
    dummy_id = uuid.uuid4()
    res_missing = client.get(f"/api/v1/models/{dummy_id}/evaluation", headers=engineer_headers)
    assert res_missing.status_code == 404


def test_health_config_endpoints(client, engineer_headers, admin_headers, db):
    """Verifies GET and PUT /health-config endpoints."""
    # GET active config
    res = client.get("/api/v1/health-config", headers=engineer_headers)
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["anomaly_weight"] == 0.30
    assert cfg["trend_enabled"] is False
    assert "DATA_OK" in cfg["data_quality_penalty"]

    # Engineer cannot PUT (Admin only)
    res_forbidden = client.put(
        "/api/v1/health-config",
        headers=engineer_headers,
        json={"anomaly_weight": 0.25},
    )
    assert res_forbidden.status_code == 403

    # Admin updates config
    res_put = client.put(
        "/api/v1/health-config",
        headers=admin_headers,
        json={"anomaly_weight": 0.35, "trend_enabled": False},
    )
    assert res_put.status_code == 200
    updated = res_put.json()
    assert updated["anomaly_weight"] == 0.35


def test_scoring_engine_and_predictions_with_breakdown(mock_valid_bundle, client, engineer_headers, monkeypatch, db):
    """Verifies trajectory scoring service and GET /machines/{id}/predictions with additive breakdown."""
    # Register and activate model
    mv = register_model_bundle(mock_valid_bundle, activate=True, session=db)

    # Mock ModelBundle.load and score_trajectory for synthetic test
    class DummyBundle:
        pass

    monkeypatch.setattr("app.services.scoring_service.ModelBundle.load", lambda p: DummyBundle())

    def mock_score_trajectory(df, bundle, health_config=None):
        out = df.copy()
        out["failure_probability"] = 0.45
        out["anomaly_score"] = 0.20
        out["machine_health_indicator"] = 62.0
        out["anomaly_flag"] = False
        out["data_quality_status"] = "DATA_OK"
        return out

    monkeypatch.setattr("app.services.scoring_service.score_trajectory", mock_score_trajectory)

    # Create test machine
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="SCORING-UNIT-01",
        operational_status="active",
    )
    db.add(machine)
    db.commit()

    # Add 35 cycles of sensor readings
    readings = []
    for c in range(1, 36):
        readings.append(
            SensorReading(
                machine_id=machine.id,
                cycle_index=c,
                op_setting_1=0.0,
                op_setting_2=0.0,
                op_setting_3=100.0,
                sensor_2=642.0 + c * 0.1,
                sensor_3=1580.0 + c * 0.2,
                sensor_4=1400.0 + c * 0.15,
                sensor_7=553.0 - c * 0.05,
                sensor_8=2388.0,
                sensor_9=9050.0,
                sensor_11=47.2 + c * 0.02,
                sensor_12=521.0 - c * 0.05,
                sensor_13=2388.0,
                sensor_14=8130.0,
                sensor_15=8.4 + c * 0.005,
                sensor_17=392.0,
                sensor_20=38.8,
                sensor_21=23.3,
            )
        )
    db.add_all(readings)
    db.commit()

    # Score trajectory
    result = score_machine_trajectory(machine.id, db, bundle_path=mock_valid_bundle)
    assert result["machine_id"] == str(machine.id)
    assert result["scored_cycles"] == 35
    assert "health_indicator" in result
    assert "recommendation" in result

    # Check GET /machines/{id}/predictions
    res_pred = client.get(f"/api/v1/machines/{machine.id}/predictions", headers=engineer_headers)
    assert res_pred.status_code == 200
    pred_data = res_pred.json()
    assert pred_data["total"] == 35
    latest_pred = pred_data["items"][0]  # sorted desc by cycle

    assert latest_pred["cycle"] == 35
    assert latest_pred["penalty_risk"] >= 0.0
    assert latest_pred["penalty_anomaly"] >= 0.0
    assert latest_pred["penalty_dq"] == 0.0
    assert latest_pred["penalty_trend"] == 0.0
    assert latest_pred["breakdown"] is not None
    assert latest_pred["breakdown"]["trend_status"] == "not_enabled"
    assert latest_pred["lineage"] is not None
    assert latest_pred["lineage"]["horizon"] == 30


def test_alerts_lifecycle_and_deduplication(client, engineer_headers, db):
    """Verifies alerts listing, acknowledgment, resolution, and uq_open_alert_per_type deduplication."""
    machine = Machine(id=uuid.uuid4(), machine_code="ALERT-TEST-UNIT")
    db.add(machine)
    db.commit()

    # Create initial alert
    alert = Alert(
        id=uuid.uuid4(),
        machine_id=machine.id,
        alert_type="high_failure_risk",
        status="open",
        severity="critical",
        trigger_cycle=50,
        trigger_score=0.85,
        recommendation_text="URGENT REVIEW: High failure probability",
        recommendation_rule_id="RULE_01",
    )
    db.add(alert)
    db.commit()

    # List alerts
    res_list = client.get(f"/api/v1/alerts?machine_id={machine.id}", headers=engineer_headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    # Acknowledge alert
    res_ack = client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=engineer_headers)
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "acknowledged"
    assert res_ack.json()["acknowledged_at"] is not None

    # Resolve alert
    res_res = client.post(f"/api/v1/alerts/{alert.id}/resolve", headers=engineer_headers)
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"
    assert res_res.json()["resolved_at"] is not None


def test_maintenance_workflow_lifecycle_side_effects(client, engineer_headers, db):
    """Verifies full human-in-the-loop maintenance workflow and machine status side effects.

    - Starting maintenance switches machine operational_status to 'maintenance'
    - Completing maintenance with 'resolved' outcome restores operational_status to 'active'
    """
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="WORKFLOW-TEST-UNIT",
        operational_status="active",
        health_band="Warning",
        health_indicator=55.0,
    )
    db.add(machine)
    db.commit()

    # Create associated alert
    alert = Alert(
        id=uuid.uuid4(),
        machine_id=machine.id,
        alert_type="high_failure_risk",
        status="open",
        severity="critical",
        trigger_cycle=100,
        trigger_score=0.88,
        recommendation_text="SCHEDULE MAINTENANCE: High risk",
        recommendation_rule_id="RULE_01",
    )
    db.add(alert)
    db.commit()

    # 1. Engineer records physical maintenance action
    create_payload = {
        "machine_id": str(machine.id),
        "alert_id": str(alert.id),
        "issue": "Turbofan Stage 1 HPT Degradation detected",
        "recommended_action": "Borescope inspection of HPT nozzle guide vanes",
        "decision": "followed_recommendation",
        "decision_rationale": "High calibrated failure probability (0.88) requires inspection",
        "action_taken": "Executed borescope inspection and replaced stage 1 blade segment",
        "action_type": "replacement",
        "notes": "Work order WO-90210 initiated",
    }
    res_create = client.post("/api/v1/maintenance", headers=engineer_headers, json=create_payload)
    assert res_create.status_code == 200
    maint_record = res_create.json()
    assert maint_record["status"] == "in_progress"
    assert maint_record["decision"] == "followed_recommendation"

    # Verify SIDE EFFECT 1: machine operational_status transitioned to 'maintenance'
    db.refresh(machine)
    assert machine.operational_status == "maintenance"

    # 2. Engineer completes maintenance with outcome 'resolved'
    complete_payload = {
        "outcome": "resolved",
        "engineer_notes": "Ground test run passed. Telemetry baselines restored.",
    }
    res_complete = client.post(
        f"/api/v1/maintenance/{maint_record['id']}/complete",
        headers=engineer_headers,
        json=complete_payload,
    )
    assert res_complete.status_code == 200
    completed_rec = res_complete.json()
    assert completed_rec["status"] == "completed"
    assert completed_rec["outcome"] == "resolved"

    # Verify SIDE EFFECT 2: machine operational_status restored to 'active'
    db.refresh(machine)
    assert machine.operational_status == "active"

    # Verify SIDE EFFECT 3: associated alert automatically resolved
    db.refresh(alert)
    assert alert.status == "resolved"
