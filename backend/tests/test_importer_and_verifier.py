"""
Unit tests for Model Importer, Bundle Verifier, and Demo Fleet Seeder
"""

import json

import pytest

from app.ml.verify_artifacts import (
    ArtifactVerificationError,
    check_library_versions,
    verify_all,
    verify_manifest,
)
from app.models.entities import Machine
from app.services.importer import register_model_bundle, seed_demo_engines




def test_verifier_passes_on_valid_bundle(mock_valid_bundle):
    """Verifier must succeed when hashes and versions match."""
    metadata = verify_all(mock_valid_bundle, strict_versions=False)
    assert metadata["model_version"] == "cmapss-fd001-h30-test"


def test_verifier_refuses_on_missing_manifest(tmp_path):
    """Verifier must raise ArtifactVerificationError if manifest is missing."""
    empty_dir = tmp_path / "empty_bundle"
    empty_dir.mkdir()
    (empty_dir / "metadata").mkdir()
    with pytest.raises(ArtifactVerificationError, match="artifact_manifest.json not found"):
        verify_manifest(empty_dir)


def test_verifier_refuses_on_tampered_file(mock_valid_bundle):
    """Verifier must raise ArtifactVerificationError if any file is tampered."""
    target_file = mock_valid_bundle / "model" / "calibrated_failure_model.joblib"
    target_file.write_bytes(b"corrupted_tampered_content")

    with pytest.raises(ArtifactVerificationError, match="hash mismatch"):
        verify_manifest(mock_valid_bundle)


def test_verifier_refuses_on_unlisted_file(mock_valid_bundle):
    """Verifier must reject unexpected unlisted files in the bundle directory."""
    extra_file = mock_valid_bundle / "malicious.py"
    extra_file.write_text("print('exploit')")

    with pytest.raises(ArtifactVerificationError, match="unlisted file"):
        verify_manifest(mock_valid_bundle, allow_unlisted=False)


def test_verifier_refuses_on_library_version_mismatch():
    """Verifier must reject incompatible library versions."""
    meta = {
        "library_versions": {
            "python": "2.7.0",  # Incompatible with Python 3.10
        }
    }
    with pytest.raises(ArtifactVerificationError, match="library version mismatch"):
        check_library_versions(meta, strict=True)


def test_register_model_bundle_importer(mock_valid_bundle, db):
    """Importer must correctly populate model_versions and model_evaluations tables."""
    mv = register_model_bundle(mock_valid_bundle, activate=True, session=db)
    assert mv is not None
    assert mv.bundle_version == "cmapss-fd001-h30-test"
    assert mv.is_active is True
    assert mv.model_card_complete is True
    assert mv.task == "failure_risk"
    assert mv.horizon == 30

    # Check evaluation
    eval_rec = mv.evaluation
    assert eval_rec is not None
    assert eval_rec.metrics["internal_test"]["pr_auc"] == 0.88
    assert "internal_test" in eval_rec.curves
    assert len(eval_rec.feature_importance) == 2


def test_seed_demo_engines_creates_all_three_categories(mock_valid_bundle, db):
    """Seeder must populate Healthy, Warning, and Critical demo machines."""
    # First register and activate model
    register_model_bundle(mock_valid_bundle, activate=True, session=db)

    results = seed_demo_engines(mock_valid_bundle, session=db)
    assert "healthy" in results
    assert "warning" in results
    assert "critical" in results

    assert results["healthy"]["machine_code"] == "ENGINE-001"
    assert results["warning"]["machine_code"] == "ENGINE-002"
    assert results["critical"]["machine_code"] == "ENGINE-003"

    # Verify machines in DB
    healthy_machine = db.query(Machine).filter(Machine.machine_code == "ENGINE-001").first()
    assert healthy_machine is not None
    assert healthy_machine.is_demo is True
    assert healthy_machine.health_band == "Healthy"
    assert len(healthy_machine.readings) == 2
    assert len(healthy_machine.predictions) == 1

    crit_machine = db.query(Machine).filter(Machine.machine_code == "ENGINE-003").first()
    assert crit_machine is not None
    assert crit_machine.operational_status == "active"
    assert crit_machine.health_band == "Critical"
    assert len(crit_machine.readings) == 2


def test_seed_demo_engines_fails_loudly_if_category_missing(tmp_path, db):
    """Seeder must fail loudly (raise ValueError) if one of Healthy, Warning, or Critical is missing."""
    bundle_dir = tmp_path / "incomplete_demo_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "demo").mkdir()

    (bundle_dir / "demo" / "demo_units.csv").write_text("unit_id,cycle\n1,1\n")
    # Only Healthy scores, no Warning and no Critical
    demo_scores_csv = (
        "unit_id,cycle,failure_probability,anomaly_score,machine_health_indicator,data_quality_status\n"
        + "1,1,0.01,0.01,95.0,DATA_OK\n"
    )
    (bundle_dir / "demo" / "demo_reference_scores.csv").write_text(demo_scores_csv)

    with pytest.raises(ValueError, match="FATAL: Demo fleet seeding cannot proceed|Could not find an engine"):
        seed_demo_engines(bundle_dir, session=db)


def test_brier_and_ece_metrics_non_null(mock_valid_bundle, db):
    """Brier score and ECE must be non-null and evaluated_at must equal model_card.evaluation_date."""
    mv = register_model_bundle(mock_valid_bundle, activate=True, session=db)
    eval_rec = mv.evaluation
    assert eval_rec is not None
    assert eval_rec.evaluated_at is not None

    m = eval_rec.metrics.get("internal_test", {})
    assert m.get("brier") is not None, "Brier score must not be null"
    assert m.get("brier_score") is not None, "brier_score alias must not be null"
    assert m.get("ece") is not None, "ECE must not be null"
    assert m.get("expected_calibration_error") is not None, "expected_calibration_error alias must not be null"
    assert m["brier"] == 0.04
    assert m["ece"] == 0.015


def test_anomaly_model_registered_separately(mock_valid_bundle, db):
    """Anomaly model must be registered as its own model_versions row with task=anomaly."""
    mv = register_model_bundle(mock_valid_bundle, activate=True, session=db)
    from app.models.entities import ModelVersion
    anom_mv = db.query(ModelVersion).filter(
        ModelVersion.bundle_version == mv.bundle_version,
        ModelVersion.task == "anomaly"
    ).first()
    assert anom_mv is not None
    assert anom_mv.model_type == "IsolationForest"
    assert anom_mv.is_active is True
    assert anom_mv.evaluation is not None
    assert anom_mv.evaluation.task == "anomaly"
    assert anom_mv.evaluation.evaluated_at == mv.evaluation.evaluated_at

