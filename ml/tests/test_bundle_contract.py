"""
Unit tests for pdm_core.bundle (writer, validator, and CLI)
"""

import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from pdm_core.bundle import (
    validate_model_bundle,
    write_complete_bundle,
)
from pdm_core.evaluation.metrics import compute_evaluation
from pdm_core.schemas.bundle_schemas import ModelCardSchema


@pytest.fixture
def sample_complete_bundle(tmp_path):
    """Creates a valid, complete synthetic model bundle for contract testing."""
    version = "0.1.0"
    feature_config = {
        "feature_config_version": "1.0.0",
        "unit_col": "unit_id",
        "cycle_col": "cycle",
    }
    demo_df = pd.DataFrame({
        "unit_id": [1, 2],
        "cycle": [10, 20],
        "sensor_1": [500.0, 500.0],
    })

    # Fit dummy models
    X = np.array([[0.1, 0.2], [0.8, 0.9], [0.3, 0.4], [0.7, 0.6]])
    y = np.array([0, 1, 0, 1])
    scaler = StandardScaler().fit(X)
    X_scaled = scaler.transform(X)
    model = LogisticRegression().fit(X_scaled, y)

    eval_schema = compute_evaluation(
        y_true=y,
        y_prob=model.predict_proba(X_scaled)[:, 1],
        model_name="Demo Model",
        model_version=version,
        feature_names=["sensor_1", "sensor_2"],
        importances=[0.5, 0.5],
    )

    model_card = ModelCardSchema(
        model_name="Demo Failure Classifier",
        version=version,
        description="Synthetic test model card",
        model_type="logistic_regression",
        intended_use="Unit testing",
        domain="Simulated Turbofan Degradation (NASA C-MAPSS FD001)",
        training_dataset="C-MAPSS FD001 synthetic test",
        evaluation_dataset="C-MAPSS FD001 synthetic test",
        feature_summary=["sensor_1", "sensor_2"],
        operational_limitations=["For testing only"],
        author="PrediCore Team",
        created_at="2026-10-01T00:00:00Z",
    )

    failure_risk_kwargs = {
        "model": model,
        "preprocessing": scaler,
        "calibrator": model,
        "reference_stats": {"sensor_1": {"median": 500.0, "mad": 0.5}},
        "explainer_config": {"model_type": "linear", "explainer_kind": "linear"},
        "model_card": model_card,
        "evaluation": eval_schema,
        "input_features": ["sensor_1", "sensor_2"],
        "horizon": 30,
        "decision_threshold": 0.50,
        "model_type": "logistic_regression",
    }

    bundle_dir = write_complete_bundle(
        target_root=tmp_path,
        version=version,
        feature_config_content=feature_config,
        demo_candidates_df=demo_df,
        failure_risk_kwargs=failure_risk_kwargs,
    )
    return bundle_dir


def test_bundle_validation_passes(sample_complete_bundle):
    result = validate_model_bundle(sample_complete_bundle)
    assert result.valid is True
    assert len(result.errors) == 0
    assert result.manifest is not None
    assert result.evaluation is not None
    assert result.model_card is not None


def test_bundle_tampering_fails_sha256(sample_complete_bundle):
    # Tamper with reference_stats.json in failure_risk
    stats_file = sample_complete_bundle / "failure_risk" / "reference_stats.json"
    with open(stats_file, "a") as f:
        f.write("\n// tampered")

    result = validate_model_bundle(sample_complete_bundle)
    assert result.valid is False
    assert any("SHA-256 mismatch" in err for err in result.errors)


def test_bundle_cli_validate(sample_complete_bundle):
    # Run CLI: python -m pdm_core.bundle validate <path>
    cmd = [sys.executable, "-m", "pdm_core.bundle", "validate", str(sample_complete_bundle)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "BUNDLE VALIDATION PASSED" in proc.stdout
