"""
Unit tests for database CHECK constraints and UNIQUE indexes on PostgreSQL.
Verifies that invalid domain states are strictly rejected at the database level.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.entities import (
    Alert,
    Dataset,
    HealthIndicatorConfig,
    Machine,
    MaintenanceRecord,
    ModelVersion,
    SensorReading,
    User,
)


def test_health_indicator_config_anomaly_weight_constraint(db):
    # anomaly_weight > 1.0 -> must fail CheckConstraint
    invalid_config = HealthIndicatorConfig(
        id=uuid.uuid4(),
        version="2.0-invalid",
        anomaly_weight=1.5,
        data_quality_penalty={"DATA_OK": 0.0, "DATA_WARNING": 10.0},
        trend_enabled=False,
        is_active=False,
    )
    db.add(invalid_config)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Valid config passes
    valid_config = HealthIndicatorConfig(
        id=uuid.uuid4(),
        version="2.0-valid",
        anomaly_weight=0.30,
        data_quality_penalty={"DATA_OK": 0.0, "DATA_WARNING": 10.0},
        trend_enabled=False,
        is_active=False,
    )
    db.add(valid_config)
    db.commit()


def test_user_role_check_constraint(db):
    # Role not in ('admin', 'engineer') -> must fail CheckConstraint
    invalid_user = User(
        id=uuid.uuid4(),
        email="operator@predicore.io",
        password_hash="somehash",
        role="operator",
    )
    db.add(invalid_user)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_machine_operational_status_constraint(db):
    # Operational status must strictly be 'active', 'maintenance', or 'archived'
    # 'warning', 'critical', 'exploded', 'offline' must fail CheckConstraint
    invalid_machine = Machine(
        id=uuid.uuid4(),
        machine_code="invalid-status-machine",
        operational_status="critical",  # Health band is critical, operational status is active/maintenance/archived
    )
    db.add(invalid_machine)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_alert_severity_constraint(db):
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="alert-test-unit",
    )
    db.add(machine)
    db.commit()

    invalid_alert = Alert(
        id=uuid.uuid4(),
        machine_id=machine.id,
        alert_type="failure_risk",
        severity="apocalyptic",  # not in ('warning', 'critical')
        trigger_cycle=10,
        trigger_score=0.85,
        recommendation_text="Check unit",
        recommendation_rule_id="RULE_TEST",
    )
    db.add(invalid_alert)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_maintenance_outcome_constraint(db):
    admin = db.query(User).filter_by(role="admin").first()
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="maint-test-unit",
    )
    db.add(machine)
    db.commit()

    invalid_maint = MaintenanceRecord(
        id=uuid.uuid4(),
        machine_id=machine.id,
        action_type="component_replacement",
        engineer_notes="Replaced HPT blades",
        performed_by_user_id=admin.id,
        outcome="miraculous",  # not in ('resolved', 'no_issue_found', 'unresolved')
    )
    db.add(invalid_maint)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_one_active_model_per_adapter_task(db):
    """Postgres partial unique index: only 1 active model per (adapter_key, task)."""
    m1 = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="1.0.0",
        task="failure_risk",
        model_type="RandomForest",
        adapter_key="cmapss_fd001",
        feature_config_version="1.0",
        preprocessing_version="1.0",
        input_features=["sensor_2", "sensor_3"],
        is_active=True,
        model_card_complete=True,
        artifact_path="/models/v1",
        sha256_hash="abc123hash",
        python_version="3.11.0",
    )
    db.add(m1)
    db.commit()

    m2 = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="1.0.1",
        task="failure_risk",
        model_type="XGBoost",
        adapter_key="cmapss_fd001",
        feature_config_version="1.0",
        preprocessing_version="1.0",
        input_features=["sensor_2", "sensor_3"],
        is_active=True,
        model_card_complete=True,
        artifact_path="/models/v2",
        sha256_hash="def456hash",
        python_version="3.11.0",
    )
    db.add(m2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Multiple inactive models for the same (adapter, task) are allowed
    m2.is_active = False
    db.add(m2)
    db.commit()


def test_model_card_complete_check_constraint_on_activation(db):
    """Postgres CHECK constraint: a model cannot be active without a complete model card."""
    m_invalid = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="2.0.0",
        task="anomaly",
        model_type="IsolationForest",
        adapter_key="cmapss_fd001",
        feature_config_version="1.0",
        preprocessing_version="1.0",
        input_features=["sensor_2", "sensor_3"],
        is_active=True,
        model_card_complete=False,  # Violates check_model_card_complete_if_active
        artifact_path="/models/v3",
        sha256_hash="ghi789hash",
        python_version="3.11.0",
    )
    db.add(m_invalid)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_one_open_alert_per_machine_alert_type(db):
    """Postgres partial unique index: only 1 open/acknowledged alert per (machine, alert_type)."""
    machine = Machine(id=uuid.uuid4(), machine_code="alert-constraint-unit")
    db.add(machine)
    db.commit()

    alert1 = Alert(
        id=uuid.uuid4(),
        machine_id=machine.id,
        alert_type="failure_risk",
        status="open",
        severity="critical",
        trigger_cycle=10,
        trigger_score=0.9,
        recommendation_text="Immediate overhaul",
        recommendation_rule_id="RULE_01",
    )
    db.add(alert1)
    db.commit()

    alert2 = Alert(
        id=uuid.uuid4(),
        machine_id=machine.id,
        alert_type="failure_risk",
        status="open",
        severity="warning",
        trigger_cycle=12,
        trigger_score=0.8,
        recommendation_text="Inspect engine",
        recommendation_rule_id="RULE_02",
    )
    db.add(alert2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Once alert1 is resolved, alert2 can be opened
    alert1.status = "resolved"
    db.commit()

    db.add(alert2)
    db.commit()


def test_unique_machine_dataset_cycle_constraint(db):
    """Postgres unique constraint: unique(machine_id, dataset_id, cycle_index)."""
    dataset = Dataset(
        id=uuid.uuid4(),
        name="Telemetry Dataset",
        slug="telemetry-ds-test",
    )
    machine = Machine(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        machine_code="telemetry-unit-01",
    )
    db.add(dataset)
    db.add(machine)
    db.commit()

    r1 = SensorReading(
        machine_id=machine.id,
        dataset_id=dataset.id,
        cycle_index=1,
    )
    db.add(r1)
    db.commit()

    r2 = SensorReading(
        machine_id=machine.id,
        dataset_id=dataset.id,
        cycle_index=1,
    )
    db.add(r2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_dropped_machine_cycle_unique_allows_different_datasets(db):
    """Verifies that dropping uq_machine_cycle allows the same machine cycle across different datasets."""
    ds1 = Dataset(id=uuid.uuid4(), name="DS 1", slug="ds-1-unique-test")
    ds2 = Dataset(id=uuid.uuid4(), name="DS 2", slug="ds-2-unique-test")
    machine = Machine(id=uuid.uuid4(), machine_code="shared-cycle-unit")
    db.add_all([ds1, ds2, machine])
    db.commit()

    # Same machine, same cycle (1), but DIFFERENT datasets -> must succeed!
    r1 = SensorReading(machine_id=machine.id, dataset_id=ds1.id, cycle_index=1)
    r2 = SensorReading(machine_id=machine.id, dataset_id=ds2.id, cycle_index=1)
    db.add_all([r1, r2])
    db.commit()
    assert r1.id != r2.id


def test_prediction_breakdown_points_storage(db):
    """Verifies predictions store additive breakdown points (penalty_risk, penalty_anomaly, penalty_dq, penalty_trend)."""
    from app.models.entities import Prediction
    m = Machine(id=uuid.uuid4(), machine_code="pred-storage-unit")
    mv = ModelVersion(
        id=uuid.uuid4(),
        bundle_version="1.0.0",
        task="failure_risk",
        model_type="XGBoostClassifier",
        feature_config_version="1.0",
        preprocessing_version="1.0",
        input_features=["sensor_2"],
        artifact_path="/dummy",
        sha256_hash="dummyhash",
        python_version="3.10",
    )
    cfg = db.query(HealthIndicatorConfig).first()
    db.add_all([m, mv])
    db.commit()

    pred = Prediction(
        id=uuid.uuid4(),
        machine_id=m.id,
        cycle=50,
        as_of_index=50,
        dataset_version="v1",
        schema_mapping_hash="hash1",
        feature_config_version="1.0",
        preprocessing_version="1.0",
        failure_model_version_id=mv.id,
        health_config_id=cfg.id,
        horizon=30,
        failure_probability=0.45,
        risk_level="Medium",
        health_indicator=55.0,
        health_band="Warning",
        penalty_risk=45.0,
        penalty_anomaly=10.0,
        penalty_dq=0.0,
        penalty_trend=0.0,
        clipping_adjustment=0.0,
        input_window_start=20,
        input_window_end=50,
        reliability_flags={"status": "ok"},
    )
    db.add(pred)
    db.commit()

    fetched = db.get(Prediction, pred.id)
    assert fetched.penalty_risk == 45.0
    assert fetched.penalty_anomaly == 10.0
    assert fetched.penalty_dq == 0.0
    assert fetched.penalty_trend == 0.0
