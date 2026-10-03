"""
Tests for PRD Section 14 API Endpoints.
Verifies all newly built endpoints for:
- Machines (create, update metadata, archive with alert guard, timeline)
- Scoring runs (Admin auth, 409 incompatibility, background job)
- Predictions & explanations (lineage, explanation headline + trend facts)
- Anomalies
- Models (model card, 404 "Model evaluation not available.")
- Settings & Admin (risk bands, alert rules, reliability, recommendation rules, audit log)
- Dashboard (summary, priority machines, recent anomalies, recent alerts, probability distribution)
"""

import uuid

from app.models.entities import (
    Alert,
    Dataset,
    Machine,
    ModelVersion,
    SensorReading,
)
from app.services.importer import register_model_bundle
from app.services.scoring_service import run_scoring_job, score_machine_trajectory
from fastapi.testclient import TestClient


def test_dashboard_endpoints(client: TestClient, engineer_headers: dict, db):
    """Verifies all dashboard endpoints return valid structures."""
    # Summary
    res = client.get("/api/v1/dashboard/summary", headers=engineer_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_machines" in data
    assert "average_health_indicator" in data
    assert "dataset_banner_text" in data
    assert data["dataset_banner_text"] == "Demo Dataset: NASA C-MAPSS FD001 \u2014 Simulated Turbofan Engine Data"

    # Priority machines
    res = client.get("/api/v1/dashboard/priority-machines?limit=5", headers=engineer_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Recent anomalies
    res = client.get("/api/v1/dashboard/recent-anomalies?limit=5", headers=engineer_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Recent alerts
    res = client.get("/api/v1/dashboard/recent-alerts?limit=5", headers=engineer_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Probability distribution
    res = client.get("/api/v1/dashboard/probability-distribution", headers=engineer_headers)
    assert res.status_code == 200
    assert "bins" in res.json()


def test_machine_management_and_archive_guards(client: TestClient, admin_headers: dict, engineer_headers: dict, db):
    """Admin can create, update, and archive machines with open-alert guard."""
    code = f"TEST-UNIT-{uuid.uuid4().hex[:6]}"
    create_payload = {
        "machine_code": code,
        "name": "Test Engine Alpha",
        "machine_type": "Turbofan Engine",
        "location": "Test Cell 4",
        "notes": "Testing PRD 14.2",
    }
    # Non-admin fails
    res = client.post("/api/v1/machines", json=create_payload, headers=engineer_headers)
    assert res.status_code == 403

    # Admin succeeds
    res = client.post("/api/v1/machines", json=create_payload, headers=admin_headers)
    assert res.status_code == 201
    created = res.json()
    machine_id = created["id"]
    assert created["machine_code"] == code
    assert created["operational_status"] == "active"

    # Patch metadata
    res = client.patch(
        f"/api/v1/machines/{machine_id}",
        json={"location": "Test Cell 9", "notes": "Updated note"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["location"] == "Test Cell 9"

    # Add open alert to test archive blocking
    alert = Alert(
        id=uuid.uuid4(),
        machine_id=uuid.UUID(machine_id),
        alert_type="high_failure_risk",
        status="open",
        severity="critical",
        trigger_cycle=100,
        trigger_score=0.85,
        recommendation_text="Immediate inspection",
        recommendation_rule_id="RULE_1",
    )
    db.add(alert)
    db.commit()

    # Archive without force fails with 409
    res = client.post(f"/api/v1/machines/{machine_id}/archive", json={"force": False}, headers=admin_headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "OPEN_ALERTS_EXIST"

    # Archive with force=True succeeds
    res = client.post(f"/api/v1/machines/{machine_id}/archive", json={"force": True}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["operational_status"] == "archived"

    # Timeline endpoint
    res = client.get(f"/api/v1/machines/{machine_id}/timeline", headers=engineer_headers)
    assert res.status_code == 200
    timeline = res.json()
    assert timeline["machine_id"] == machine_id
    assert len(timeline["events"]) >= 1


def test_scoring_run_job_and_incompatible_rejection(
    client: TestClient, admin_headers: dict, engineer_headers: dict, mock_valid_bundle, monkeypatch, db
):
    """Scoring run endpoint rejects incompatible datasets and queues job for compatible datasets."""
    # Register active model
    register_model_bundle(mock_valid_bundle, activate=True, session=db)
    monkeypatch.setattr("app.services.scoring_service.ModelBundle.load", lambda path: object())
    monkeypatch.setattr(
        "app.services.scoring_service.score_trajectory",
        lambda df, bundle, health_config=None: df.assign(
            failure_probability=0.5, anomaly_score=0.2, anomaly_flag=False, machine_health_indicator=80.0
        ),
    )

    # Create an incompatible dataset
    bad_ds = Dataset(
        id=uuid.uuid4(),
        name="Incompatible Dataset",
        slug=f"bad-ds-{uuid.uuid4().hex[:6]}",
        filename="bad.csv",
        file_size_bytes=1000,
        row_count=100,
        status="rejected_incompatible",
        adapter_key="cmapss_fd001",
    )
    db.add(bad_ds)

    # Create a valid dataset
    good_ds = Dataset(
        id=uuid.uuid4(),
        name="Good Dataset",
        slug=f"good-ds-{uuid.uuid4().hex[:6]}",
        filename="good.csv",
        file_size_bytes=1000,
        row_count=100,
        status="valid",
        adapter_key="cmapss_fd001",
    )
    db.add(good_ds)
    db.commit()

    # Engineer cannot trigger scoring runs
    res = client.post(
        "/api/v1/scoring-runs",
        json={"dataset_id": str(good_ds.id)},
        headers=engineer_headers,
    )
    assert res.status_code == 403

    # Incompatible dataset rejected with 409
    res = client.post(
        "/api/v1/scoring-runs",
        json={"dataset_id": str(bad_ds.id)},
        headers=admin_headers,
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "DATASET_INCOMPATIBLE"

    # Compatible dataset accepted with 202
    res = client.post(
        "/api/v1/scoring-runs",
        json={"dataset_id": str(good_ds.id)},
        headers=admin_headers,
    )
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["status"] == "queued"

    # Run the scoring job synchronously with _db to test execution logic
    run_scoring_job(
        job_id=uuid.UUID(data["job_id"]),
        dataset_id=good_ds.id,
        bundle_path=mock_valid_bundle,
        _db=db,
    )


def test_predictions_and_explanation_endpoints(
    client: TestClient, engineer_headers: dict, mock_valid_bundle, monkeypatch, db
):
    """Verifies predictions retrieval and explanation generation."""
    register_model_bundle(mock_valid_bundle, activate=True, session=db)

    def mock_score_trajectory(df, bundle, health_config=None):
        out = df.copy()
        out["failure_probability"] = 0.72
        out["anomaly_score"] = 0.85
        out["anomaly_flag"] = True
        out["machine_health_indicator"] = 38.0
        out["data_quality_status"] = "DATA_OK"
        return out

    monkeypatch.setattr("app.services.scoring_service.score_trajectory", mock_score_trajectory)
    monkeypatch.setattr("app.services.scoring_service.ModelBundle.load", lambda path: object())

    m = Machine(
        id=uuid.uuid4(),
        machine_code=f"PRED-EXP-{uuid.uuid4().hex[:6]}",
        operational_status="active",
    )
    db.add(m)
    db.commit()

    # Add readings
    readings = [
        SensorReading(
            machine_id=m.id,
            cycle_index=c,
            op_setting_1=0.0,
            op_setting_2=0.0,
            op_setting_3=100.0,
            sensor_2=642.0 + c * 0.1,
            sensor_11=47.0 + c * 0.05,
        )
        for c in range(1, 35)
    ]
    db.add_all(readings)
    db.commit()

    score_machine_trajectory(m.id, db, bundle_path=mock_valid_bundle)

    # GET /machines/{id}/predictions/latest
    res = client.get(f"/api/v1/machines/{m.id}/predictions/latest", headers=engineer_headers)
    assert res.status_code == 200
    pred = res.json()
    pred_id = pred["id"]
    assert pred["failure_probability"] == 0.72
    assert "breakdown" in pred
    assert "lineage" in pred

    # GET /predictions/{id}
    res = client.get(f"/api/v1/predictions/{pred_id}", headers=engineer_headers)
    assert res.status_code == 200
    assert res.json()["id"] == pred_id

    # GET /predictions/{id}/explanation
    res = client.get(f"/api/v1/predictions/{pred_id}/explanation", headers=engineer_headers)
    assert res.status_code == 200
    expl = res.json()
    assert "headline" in expl
    assert "contributions" in expl
    assert "trend_facts" in expl
    assert "text" in expl
    assert "Failure probability" in expl["text"]


def test_settings_and_admin_endpoints(client: TestClient, admin_headers: dict, engineer_headers: dict, db):
    """Verifies risk bands, alert rules, reliability, and admin audit log endpoints."""
    # Risk bands GET
    res = client.get("/api/v1/settings/risk-bands", headers=engineer_headers)
    assert res.status_code == 200
    assert "low_max" in res.json()

    # Risk bands PUT (Admin only)
    res = client.put(
        "/api/v1/settings/risk-bands",
        json={"low_max": 0.25, "medium_max": 0.55, "high_max": 0.85},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["low_max"] == 0.25

    # Alert rules GET
    res = client.get("/api/v1/settings/alert-rules", headers=engineer_headers)
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 1
    rule_id = rules[0]["rule_id"]

    # Alert rules PUT
    res = client.put(
        f"/api/v1/settings/alert-rules/{rule_id}",
        json={"consecutive_cycles": 5},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["consecutive_cycles"] == 5

    # Reliability & Recommendation rules (Read-only)
    res = client.get("/api/v1/settings/reliability", headers=engineer_headers)
    assert res.status_code == 200
    assert res.json()["min_window_length"] == 30

    res = client.get("/api/v1/settings/recommendation-rules", headers=engineer_headers)
    assert res.status_code == 200
    assert "rules" in res.json()

    # Admin audit log
    res = client.get("/api/v1/admin/audit-log", headers=admin_headers)
    assert res.status_code == 200
    assert "items" in res.json()


def test_model_card_and_empty_evaluation_state(client: TestClient, engineer_headers: dict, db):
    """Model card endpoint returns metadata; evaluation endpoint returns exact error when missing."""
    mv = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="no-eval-test-model",
        task="failure_risk",
        model_type="XGBoostClassifier",
        adapter_key="cmapss_fd001",
        feature_config_version="v1.0",
        preprocessing_version="v1.0",
        input_features=["sensor_2", "sensor_3"],
        horizon=30,
        horizon_unit="cycles",
        decision_threshold=0.50,
        is_active=False,
        model_card_complete=True,
        artifact_path="/nonexistent/bundle",
        sha256_hash="dummyhash",
        python_version="3.10.0",
    )
    db.add(mv)
    db.commit()

    # Model Card
    res = client.get(f"/api/v1/models/{mv.id}/card", headers=engineer_headers)
    assert res.status_code == 200
    assert res.json()["model_version"] == "no-eval-test-model"

    # Evaluation endpoint returns 404 with exact message "Model evaluation not available."
    res = client.get(f"/api/v1/models/{mv.id}/evaluation", headers=engineer_headers)
    assert res.status_code == 404
    assert res.json()["error"]["message"] == "Model evaluation not available."
