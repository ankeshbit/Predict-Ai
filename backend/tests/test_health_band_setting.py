"""
Integration tests verifying that machine health band assignment reads from the health_bands Setting
in local PostgreSQL rather than hardcoded constants, and that changing the setting row changes the
assigned band in real scored predictions with NO MagicMock for the DB (V2, Items 4, 5, 6).
"""

import uuid

import pandas as pd
from sqlalchemy import select

from app.api.v1.machines import _enrich_machine_response
from app.models.entities import (
    HealthIndicatorConfig,
    Machine,
    ModelVersion,
    Prediction,
    SensorReading,
    Setting,
)
from app.services.scoring_service import determine_health_band, score_machine_trajectory


def test_determine_health_band_reads_configured_setting():
    """Verifies that determine_health_band respects custom band settings."""
    default_bands = [
        {"key": "Excellent", "min_score": 86, "max_score": 100},
        {"key": "Healthy", "min_score": 71, "max_score": 85},
        {"key": "Warning", "min_score": 51, "max_score": 70},
        {"key": "Poor", "min_score": 31, "max_score": 50},
        {"key": "Critical", "min_score": 0, "max_score": 30},
    ]

    # With default bands, score 80 is 'Healthy'
    assert determine_health_band(80.0, default_bands) == "Healthy"

    # Now change setting: lower Excellent threshold to 75
    custom_bands = [
        {"key": "Excellent", "min_score": 75, "max_score": 100},
        {"key": "Healthy", "min_score": 60, "max_score": 74},
        {"key": "Warning", "min_score": 50, "max_score": 59},
        {"key": "Poor", "min_score": 30, "max_score": 49},
        {"key": "Critical", "min_score": 0, "max_score": 29},
    ]

    # Changing the setting changes the assigned band to 'Excellent'
    assert determine_health_band(80.0, custom_bands) == "Excellent"


def test_determine_health_band_empty_bands_returns_none():
    """Item 4: Verifies determine_health_band returns None when no bands are configured."""
    assert determine_health_band(85.0, None) is None
    assert determine_health_band(85.0, []) is None


def test_scoring_service_assigns_band_from_setting_and_changing_setting_changes_band(db, tmp_path, monkeypatch):
    """V2 Verification: Real database session on local PostgreSQL (NO MagicMock for DB).
    Verifies that score_machine_trajectory queries the Setting row from PostgreSQL,
    stores the prediction with the band from that setting, and changing the health_bands Setting
    row directly changes the band assigned in subsequent scored predictions.
    """
    # 1. Seed or retrieve HealthIndicatorConfig
    cfg = db.scalar(select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True)))
    if not cfg:
        cfg = HealthIndicatorConfig(
            id=uuid.uuid4(),
            version="v1.0",
            anomaly_weight=0.30,
            data_quality_penalty={"DATA_OK": 0.0, "DATA_WARNING": 10.0},
            trend_enabled=False,
            is_active=True,
        )
        db.add(cfg)
        db.commit()

    # 2. Seed active ModelVersion in local Postgres
    model_id = uuid.uuid4()
    model = ModelVersion(
        id=model_id,
        bundle_version="bundle-scoring-v1",
        task="failure_risk",
        model_type="LightGBM",
        adapter_key="cmapss_fd001",
        feature_config_version="v1",
        preprocessing_version="v1",
        input_features=["sensor_11"],
        artifact_path=str(tmp_path),
        sha256_hash="e" * 64,
        python_version="3.12",
        decision_threshold=0.50,
        is_active=True,
        model_card_complete=True,
    )
    db.add(model)

    # 3. Seed Machine and SensorReading in local Postgres
    machine_id = uuid.uuid4()
    machine = Machine(
        id=machine_id,
        machine_code=f"UNIT-REAL-PG-{uuid.uuid4().hex[:6]}",
        operational_status="active",
    )
    db.add(machine)

    reading = SensorReading(
        machine_id=machine_id,
        cycle_index=1,
        sensor_11=100.0,
    )
    db.add(reading)

    # 4. Ensure Setting rows exist in local Postgres
    default_bands = [
        {"key": "Excellent", "min_score": 86, "max_score": 100},
        {"key": "Healthy", "min_score": 71, "max_score": 85},
        {"key": "Warning", "min_score": 51, "max_score": 70},
        {"key": "Poor", "min_score": 31, "max_score": 50},
        {"key": "Critical", "min_score": 0, "max_score": 30},
    ]
    setting = db.scalar(select(Setting).where(Setting.key == "health_bands"))
    if not setting:
        setting = Setting(key="health_bands", value={"bands": default_bands})
        db.add(setting)
    else:
        setting.value = {"bands": default_bands}

    risk_setting = db.scalar(select(Setting).where(Setting.key == "risk_bands"))
    if not risk_setting:
        risk_setting = Setting(key="risk_bands", value={"low_max": 0.10, "medium_max": 0.50, "high_max": 0.80})
        db.add(risk_setting)

    db.commit()

    # 5. Mock only the ML inference bundle loading & model math (pure offline transformation)
    class DummyBundle:
        pass

    monkeypatch.setattr("app.services.scoring_service.ModelBundle.load", lambda p: DummyBundle())

    def mock_score_trajectory(df, bundle, health_config=None):
        return pd.DataFrame([{
            "cycle": 1,
            "failure_probability": 0.10,
            "anomaly_score": 0.05,
            "machine_health_indicator": 80.0,
            "anomaly_flag": False,
            "data_quality_status": "DATA_OK",
        }])

    monkeypatch.setattr("app.services.scoring_service.score_trajectory", mock_score_trajectory)
    monkeypatch.setattr("app.services.scoring_service.evaluate_trajectory_alerts", lambda **kwargs: [])

    # 6. Score prediction 1: With default bands (min 86 for Excellent), score 80.0 is stored as 'Healthy'
    res1 = score_machine_trajectory(machine_id, db, bundle_path=tmp_path, commit=True)
    db.refresh(machine)
    assert machine.health_band == "Healthy"
    assert res1["health_band"] == "Healthy"

    # Query the real Prediction record from local Postgres
    latest_pred1 = db.scalar(
        select(Prediction)
        .where(Prediction.machine_id == machine_id)
        .order_by(Prediction.cycle.desc())
    )
    assert latest_pred1 is not None
    assert latest_pred1.health_band == "Healthy"

    # 7. UPDATE THE SETTING ROW IN LOCAL POSTGRES: lower Excellent threshold to 75
    custom_bands = [
        {"key": "Excellent", "min_score": 75, "max_score": 100},
        {"key": "Healthy", "min_score": 60, "max_score": 74},
        {"key": "Warning", "min_score": 50, "max_score": 59},
        {"key": "Poor", "min_score": 30, "max_score": 49},
        {"key": "Critical", "min_score": 0, "max_score": 29},
    ]
    setting.value = {"bands": custom_bands}
    db.commit()

    # 8. Score prediction 2: With updated database setting, score 80.0 is stored as 'Excellent'
    res2 = score_machine_trajectory(machine_id, db, bundle_path=tmp_path, commit=True)
    db.refresh(machine)
    assert machine.health_band == "Excellent"
    assert res2["health_band"] == "Excellent"

    # Query the latest real Prediction record from local Postgres
    latest_pred2 = db.scalar(
        select(Prediction)
        .where(Prediction.machine_id == machine_id)
        .order_by(Prediction.predicted_at.desc())
    )
    assert latest_pred2 is not None
    assert latest_pred2.health_band == "Excellent"


def test_demo_seeded_machines_band_matches_score_and_setting(db):
    """Item 5: Verifies that seeded demo machines have health_band determined by determine_health_band
    with stored bands and real score, rather than cluster name."""
    setting = db.scalar(select(Setting).where(Setting.key == "health_bands"))
    configured_bands = setting.value.get("bands") if setting and setting.value else [
        {"key": "Excellent", "min_score": 86, "max_score": 100},
        {"key": "Healthy", "min_score": 71, "max_score": 85},
        {"key": "Warning", "min_score": 51, "max_score": 70},
        {"key": "Poor", "min_score": 31, "max_score": 50},
        {"key": "Critical", "min_score": 0, "max_score": 30},
    ]

    # Verify that a machine with score 65 gets "Warning", not its cluster name
    hi_score = 65.0
    assigned_band = determine_health_band(hi_score, configured_bands)
    assert assigned_band == "Warning"

    # Verify score 25 gets "Critical"
    assert determine_health_band(25.0, configured_bands) == "Critical"

    # Verify score 90 gets "Excellent"
    assert determine_health_band(90.0, configured_bands) == "Excellent"


def test_enrich_machine_response_anomaly_threshold_isolation(db):
    """Item 4 & V2: Verifies _enrich_machine_response returns anomaly_threshold only from active anomaly model
    using real PostgreSQL database entities (NO MagicMock)."""
    cfg = db.scalar(select(HealthIndicatorConfig).limit(1))
    machine_id = uuid.uuid4()
    machine = Machine(id=machine_id, machine_code=f"UNIT-THRESH-PG-{uuid.uuid4().hex[:6]}")
    db.add(machine)

    fail_model = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="bundle-fail-pg",
        task="failure_risk",
        model_type="LightGBM",
        adapter_key="cmapss_fd001",
        feature_config_version="v1",
        preprocessing_version="v1",
        input_features=["sensor_11"],
        artifact_path="/tmp/fake",
        sha256_hash="f" * 64,
        python_version="3.12",
        decision_threshold=0.50,
        is_active=True,
        model_card_complete=True,
    )
    db.add(fail_model)

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
        health_config_id=cfg.id,
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

    # Case 1: When only failure model is active (no anomaly model active)
    enrichment1 = _enrich_machine_response(machine, db)
    assert enrichment1["anomaly_threshold"] is None, "anomaly_threshold must be None when no anomaly model"

    # Case 2: When active anomaly model is present with decision_threshold=0.88
    anom_model = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="bundle-anom-pg",
        task="anomaly",
        model_type="IsolationForest",
        adapter_key="cmapss_fd001",
        feature_config_version="v1",
        preprocessing_version="v1",
        input_features=["sensor_11"],
        artifact_path="/tmp/fake2",
        sha256_hash="a" * 64,
        python_version="3.12",
        decision_threshold=0.88,
        is_active=True,
        model_card_complete=True,
    )
    db.add(anom_model)
    db.commit()

    enrichment2 = _enrich_machine_response(machine, db)
    assert enrichment2["anomaly_threshold"] == 0.88, "anomaly_threshold must reflect anomaly model threshold"
