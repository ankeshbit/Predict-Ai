"""
Unit tests for database CHECK constraints.
Verifies that invalid domain states are strictly rejected at the database level.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.entities import Alert, HealthIndicatorConfig, Machine, MaintenanceRecord, User


def test_health_indicator_config_weight_sum_constraint(db):
    # Weights sum to 90 (not 100) -> must fail CheckConstraint
    invalid_config = HealthIndicatorConfig(
        id=uuid.uuid4(),
        version="2.0-invalid",
        weight_risk=50.0,
        weight_anomaly=20.0,
        weight_trend=20.0,  # 50 + 20 + 20 = 90 != 100
        trend_window=20,
        is_active=False,
    )
    db.add(invalid_config)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


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
    # Operational status not in allowed list
    invalid_machine = Machine(
        id=uuid.uuid4(),
        machine_code="invalid-status-machine",
        operational_status="exploded",
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
