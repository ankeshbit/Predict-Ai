"""
Unit tests verifying that machine health band assignment reads from the health_bands Setting
rather than hardcoded constants, and that changing the setting changes the assigned band (Item 6).
"""

import uuid
from unittest.mock import MagicMock
import pandas as pd

from app.models.entities import Machine, Setting
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


def test_scoring_service_assigns_band_from_setting_and_changing_setting_changes_band(tmp_path, monkeypatch):
    """Integration test verifying that score_machine_trajectory queries Setting(key='health_bands')
    and updating the setting changes the assigned band on the machine."""
    machine_id = uuid.uuid4()
    machine = Machine(
        id=machine_id,
        machine_code="UNIT-BAND-01",
        operational_status="active",
    )

    # Mock ModelBundle and score_trajectory
    class DummyBundle:
        pass

    monkeypatch.setattr("app.services.scoring_service.ModelBundle.load", lambda p: DummyBundle())

    def mock_score_trajectory(df, bundle, health_config=None):
        out = pd.DataFrame([{
            "cycle": 10,
            "failure_probability": 0.10,
            "anomaly_score": 0.05,
            "machine_health_indicator": 80.0,
            "anomaly_flag": False,
            "data_quality_status": "DATA_OK",
        }])
        return out

    monkeypatch.setattr("app.services.scoring_service.score_trajectory", mock_score_trajectory)
    monkeypatch.setattr("app.services.scoring_service.evaluate_trajectory_alerts", lambda **kwargs: [])

    # Default bands setting (min_score 86 for Excellent)
    bands_setting = Setting(
        key="health_bands",
        value={
            "bands": [
                {"key": "Excellent", "min_score": 86, "max_score": 100},
                {"key": "Healthy", "min_score": 71, "max_score": 85},
                {"key": "Warning", "min_score": 51, "max_score": 70},
                {"key": "Poor", "min_score": 31, "max_score": 50},
                {"key": "Critical", "min_score": 0, "max_score": 30},
            ]
        },
    )

    risk_setting = Setting(
        key="risk_bands",
        value={"low_max": 0.10, "medium_max": 0.50, "high_max": 0.80},
    )

    mock_db = MagicMock()
    mock_db.get.return_value = machine

    # Active model and sensor reading mocks
    active_model = MagicMock()
    active_model.id = uuid.uuid4()
    active_model.horizon = 30
    active_model.horizon_unit = "cycles"
    active_model.decision_threshold = 0.10
    active_model.feature_config_version = "v1"
    active_model.preprocessing_version = "v1"

    # Set up scalar returns for score_machine_trajectory:
    def scalar_mock(query):
        params = list(query.compile().params.values())
        if "health_bands" in params:
            return bands_setting
        if "risk_bands" in params:
            return risk_setting
        if "health_indicator_configs" in str(query):
            return None
        return active_model

    mock_db.scalar.side_effect = scalar_mock
    mock_db.scalars.return_value.all.return_value = [
        MagicMock(cycle_index=1, to_dict=lambda: {"cycle": 1, "sensor_1": 1.0})
    ]

    # First score: with default setting (min 86 for Excellent), score 80.0 gets 'Healthy'
    score_machine_trajectory(machine_id, mock_db, bundle_path=tmp_path, commit=False)
    assert machine.health_band == "Healthy", f"Expected 'Healthy', got {machine.health_band}"

    # Now change the setting: lower Excellent threshold to 75
    bands_setting.value = {
        "bands": [
            {"key": "Excellent", "min_score": 75, "max_score": 100},
            {"key": "Healthy", "min_score": 60, "max_score": 74},
            {"key": "Warning", "min_score": 50, "max_score": 59},
            {"key": "Poor", "min_score": 30, "max_score": 49},
            {"key": "Critical", "min_score": 0, "max_score": 29},
        ]
    }

    # Rescore: with updated setting, score 80.0 gets 'Excellent'!
    score_machine_trajectory(machine_id, mock_db, bundle_path=tmp_path, commit=False)
    assert machine.health_band == "Excellent", f"Expected 'Excellent', got {machine.health_band}"


def test_enrich_machine_response_anomaly_threshold_isolation():
    """Verifies that _enrich_machine_response does not use failure model decision_threshold as anomaly_threshold (Item 4)."""
    from app.api.v1.machines import _enrich_machine_response
    from app.models.entities import ModelVersion, Prediction

    machine_id = uuid.uuid4()
    machine = Machine(id=machine_id, machine_code="UNIT-THRESH-01")

    pred = Prediction(
        id=uuid.uuid4(),
        machine_id=machine_id,
        cycle=10,
        horizon=30,
        horizon_unit="cycles",
        failure_probability=0.25,
        risk_level="Low",
        penalty_anomaly=10.0,
        reliability_flags={"data_quality": "DATA_OK"},
    )

    # Case 1: When only failure model is active (no anomaly model active)
    mock_db = MagicMock()
    mock_db.scalar.side_effect = [pred, 10, None, None]

    enrichment1 = _enrich_machine_response(machine, mock_db)
    assert enrichment1["anomaly_threshold"] is None, "anomaly_threshold must be None when no anomaly model"

    # Case 2: When active anomaly model is present with decision_threshold=0.88
    anom_model = ModelVersion(id=uuid.uuid4(), task="anomaly", decision_threshold=0.88, is_active=True)
    mock_db.scalar.side_effect = [pred, 10, None, anom_model]

    enrichment2 = _enrich_machine_response(machine, mock_db)
    assert enrichment2["anomaly_threshold"] == 0.88, "anomaly_threshold must reflect anomaly model threshold"

