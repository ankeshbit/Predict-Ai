"""
Unit and integration tests for machine fleet listing, filtering, detail, and telemetry downsampling.
"""

import uuid
from datetime import datetime, timezone

from app.models.entities import Machine, ModelVersion, Prediction, SensorReading


def test_list_machines_and_filtering(client, engineer_headers, db):
    # Seed 3 test machines
    m1 = Machine(
        id=uuid.uuid4(),
        machine_code="eng-v1-u01",
        operational_status="active",
        health_band="Healthy",
        health_indicator=82.5,
        is_demo=True,
    )
    m2 = Machine(
        id=uuid.uuid4(),
        machine_code="eng-v1-u02",
        operational_status="maintenance",
        health_band="Critical",
        health_indicator=24.0,
        is_demo=True,
    )
    m3 = Machine(
        id=uuid.uuid4(),
        machine_code="prod-v1-u01",
        operational_status="archived",
        health_band="Excellent",
        health_indicator=95.0,
        is_demo=False,
    )
    db.add_all([m1, m2, m3])
    db.commit()

    # List all
    res = client.get("/api/v1/machines", headers=engineer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Filter by operational_status
    res_maint = client.get("/api/v1/machines?operational_status=maintenance", headers=engineer_headers)
    assert res_maint.status_code == 200
    data_maint = res_maint.json()
    assert data_maint["total"] == 1
    assert data_maint["items"][0]["machine_code"] == "eng-v1-u02"

    # Filter by is_demo
    res_demo = client.get("/api/v1/machines?is_demo=true", headers=engineer_headers)
    assert res_demo.status_code == 200
    assert res_demo.json()["total"] == 2

    # Search filter
    res_search = client.get("/api/v1/machines?search=prod", headers=engineer_headers)
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["machine_code"] == "prod-v1-u01"


def test_get_machine_details_and_404(client, engineer_headers, db):
    machine_id = uuid.uuid4()
    m = Machine(
        id=machine_id,
        machine_code="detail-unit-01",
        operational_status="active",
        health_band="healthy",
        health_indicator=78.0,
    )
    db.add(m)
    db.commit()

    # Success
    res = client.get(f"/api/v1/machines/{machine_id}", headers=engineer_headers)
    assert res.status_code == 200
    assert res.json()["machine_code"] == "detail-unit-01"

    # Not found
    random_id = uuid.uuid4()
    res_404 = client.get(f"/api/v1/machines/{random_id}", headers=engineer_headers)
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "NOT_FOUND"


def test_sensor_telemetry_history_downsampling(client, engineer_headers, db):
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="telemetry-unit-01",
    )
    db.add(machine)
    db.commit()

    # Add 100 cycles of telemetry
    readings = []
    for c in range(1, 101):
        readings.append(
            SensorReading(
                id=c,
                machine_id=machine.id,
                cycle=c,
                recorded_at=datetime.now(timezone.utc),
                sensor_2=640.0 + c * 0.1,
                sensor_3=1580.0 + c * 0.2,
                sensor_4=1400.0 + c * 0.05,
            )
        )
    db.add_all(readings)
    db.commit()

    # Query full history
    res_full = client.get(f"/api/v1/machines/{machine.id}/sensors", headers=engineer_headers)
    assert res_full.status_code == 200
    data_full = res_full.json()
    assert data_full["total_cycles"] == 100
    assert len(data_full["readings"]) == 100

    # Query downsampled to 20 points
    res_down = client.get(
        f"/api/v1/machines/{machine.id}/sensors?downsample_to=20",
        headers=engineer_headers,
    )
    assert res_down.status_code == 200
    data_down = res_down.json()
    assert data_down["total_cycles"] == 100
    # Downsampled length should be <= 20
    assert len(data_down["readings"]) <= 20
    assert len(data_down["readings"]) > 0
    # First cycle must be 1 and last cycle must be 100
    assert data_down["readings"][0]["cycle"] == 1
    assert data_down["readings"][-1]["cycle"] == 100


def test_anomaly_threshold_isolated_from_failure_model(client, engineer_headers, db):
    """Verifies that failure model decision_threshold is NEVER returned as anomaly_threshold (Item 4)."""
    machine_id = uuid.uuid4()
    machine = Machine(
        id=machine_id,
        machine_code="unit-thresh-test",
        operational_status="active",
    )
    db.add(machine)

    # Active failure model with decision_threshold=0.50
    fail_model = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="bundle-fail-v1",
        task="failure_risk",
        model_type="LightGBM Classifier",
        adapter_key="cmapss",
        feature_config_version="v1",
        preprocessing_version="v1",
        artifact_path="/tmp/fake",
        sha256_hash="f" * 64,
        python_version="3.12",
        decision_threshold=0.50,
        is_active=True,
        model_card_complete=True,
    )
    db.add(fail_model)

    # Prediction record for the machine
    pred = Prediction(
        id=uuid.uuid4(),
        machine_id=machine_id,
        cycle=10,
        as_of_index=10,
        dataset_version="v1",
        schema_mapping_hash="h" * 64,
        feature_config_version="v1",
        preprocessing_version="v1",
        failure_model_version_id=fail_model.id,
        horizon=30,
        horizon_unit="cycles",
        failure_probability=0.25,
        risk_level="Low",
        health_indicator=85.0,
        health_band="Healthy",
        penalty_risk=25.0,
        penalty_anomaly=10.0,
        penalty_dq=0.0,
        penalty_trend=0.0,
        clipping_adjustment=0.0,
        input_window_start=1,
        input_window_end=10,
        reliability_flags={"data_quality": "DATA_OK"},
    )
    db.add(pred)
    db.commit()

    # When only failure model is active, anomaly_threshold MUST be null (None)
    res = client.get(f"/api/v1/machines/{machine_id}", headers=engineer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["anomaly_threshold"] is None

    # Now add an active anomaly model with decision_threshold=0.88
    anom_model = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="bundle-anom-v1",
        task="anomaly",
        model_type="Isolation Forest",
        adapter_key="cmapss",
        feature_config_version="v1",
        preprocessing_version="v1",
        artifact_path="/tmp/fake2",
        sha256_hash="a" * 64,
        python_version="3.12",
        decision_threshold=0.88,
        is_active=True,
        model_card_complete=True,
    )
    db.add(anom_model)
    db.commit()

    # Now anomaly_threshold MUST reflect the anomaly model's own threshold
    res_with_anom = client.get(f"/api/v1/machines/{machine_id}", headers=engineer_headers)
    assert res_with_anom.status_code == 200
    data_with_anom = res_with_anom.json()
    assert data_with_anom["anomaly_threshold"] == 0.88

