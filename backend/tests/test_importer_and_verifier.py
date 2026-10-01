"""
Unit tests for Model Importer, Bundle Verifier, and Demo Fleet Seeder
"""

import json
from pathlib import Path
import pytest

from app.ml.verify_artifacts import (
    ArtifactVerificationError,
    check_library_versions,
    verify_all,
    verify_manifest,
)
from app.models.entities import Machine, ModelEvaluation, ModelVersion, Prediction, SensorReading
from app.services.importer import register_model_bundle, seed_demo_engines


@pytest.fixture
def mock_valid_bundle(tmp_path):
    """Creates a temporary valid bundle structure matching production layout."""
    bundle_dir = tmp_path / "cmapss-fd001-h30-test"
    bundle_dir.mkdir()
    (bundle_dir / "metadata").mkdir()
    (bundle_dir / "evaluation").mkdir()
    (bundle_dir / "demo").mkdir()
    (bundle_dir / "model").mkdir()

    # Dummy model file
    model_file = bundle_dir / "model" / "calibrated_failure_model.joblib"
    model_file.write_bytes(b"dummy_model_bytes")

    # Metadata
    metadata_content = {
        "model_version": "cmapss-fd001-h30-test",
        "dataset": "NASA C-MAPSS FD001",
        "library_versions": {
            "python": "3.10.0",
            "pytest": pytest.__version__,
        },
    }
    (bundle_dir / "metadata" / "model_metadata.json").write_text(json.dumps(metadata_content))

    model_card = {
        "model_version": "cmapss-fd001-h30-test",
        "training_timestamp": "2026-10-01T12:00:00Z",
        "evaluation_date": "2026-10-01T12:00:00Z",
        "dataset": {"name": "NASA C-MAPSS FD001"},
        "features": {"active_sensors": ["sensor_2", "sensor_3", "sensor_4"]},
        "failure_horizon": {"value": 30, "unit": "operating_cycles", "status": "configured_not_optimized"},
        "training_methodology": {
            "selected_model": "XGBoostClassifier",
            "threshold": {"value": 0.48, "rule": "F2 max"},
        },
        "evaluation_methodology": ["held-out internal test", "official test"],
        "metrics": {"internal_test": {"pr_auc": 0.88, "roc_auc": 0.95}},
        "limitations": ["Simulated turbofan engine data only", "Horizon H=30 configured not optimized"],
    }
    (bundle_dir / "metadata" / "model_card.json").write_text(json.dumps(model_card))

    curves = {
        "meta": {"model_version": "cmapss-fd001-h30-test"},
        "internal_test": {
            "confusion_matrix": {"tn": 100, "fp": 5, "fn": 4, "tp": 20},
            "calibration": {"brier_calibrated": 0.04},
            "roc": {"fpr": [0.0, 0.1, 1.0], "tpr": [0.0, 0.8, 1.0]},
            "precision_recall": {"precision": [1.0, 0.8, 0.5], "recall": [0.0, 0.8, 1.0]},
        },
        "official_test_all_rows": {
            "confusion_matrix": {"tn": 200, "fp": 10, "fn": 8, "tp": 40},
        },
    }
    (bundle_dir / "evaluation" / "curves.json").write_text(json.dumps(curves))

    feature_importance = {
        "model_version": "cmapss-fd001-h30-test",
        "features": [
            {"feature": "sensor_2__roll_10", "importance": 0.25},
            {"feature": "sensor_3__roll_10", "importance": 0.18},
        ],
    }
    (bundle_dir / "evaluation" / "feature_importance.json").write_text(json.dumps(feature_importance))

    # Demo files
    demo_units_csv = (
        "unit_id,cycle,op_setting_1,op_setting_2,op_setting_3," + ",".join(f"sensor_{i}" for i in range(1, 22)) + "\n"
        + "1,1,0.0,0.0,100.0," + ",".join("10.0" for _ in range(21)) + "\n"
        + "1,2,0.0,0.0,100.0," + ",".join("10.5" for _ in range(21)) + "\n"
        + "2,1,0.0,0.0,100.0," + ",".join("20.0" for _ in range(21)) + "\n"
        + "2,10,0.0,0.0,100.0," + ",".join("20.5" for _ in range(21)) + "\n"
        + "3,1,0.0,0.0,100.0," + ",".join("30.0" for _ in range(21)) + "\n"
        + "3,50,0.0,0.0,100.0," + ",".join("30.5" for _ in range(21)) + "\n"
    )
    (bundle_dir / "demo" / "demo_units.csv").write_text(demo_units_csv)

    demo_scores_csv = (
        "unit_id,cycle,failure_probability,anomaly_score,machine_health_indicator,data_quality_status\n"
        + "1,2,0.02,0.05,92.5,DATA_OK\n"   # Healthy
        + "2,10,0.35,0.40,62.0,DATA_OK\n"  # Warning
        + "3,50,0.85,0.90,20.0,DATA_OK\n"  # Critical
    )
    (bundle_dir / "demo" / "demo_reference_scores.csv").write_text(demo_scores_csv)

    # Generate manifest
    import hashlib
    files_manifest = {}
    for p in sorted(bundle_dir.rglob("*")):
        if p.is_file() and p.name != "artifact_manifest.json":
            rel = p.relative_to(bundle_dir).as_posix()
            files_manifest[rel] = {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "bytes": p.stat().st_size,
            }

    manifest_payload = {
        "model_version": "cmapss-fd001-h30-test",
        "hash_algorithm": "sha256",
        "files": files_manifest,
    }
    (bundle_dir / "metadata" / "artifact_manifest.json").write_text(json.dumps(manifest_payload))

    return bundle_dir


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
    mv = register_model_bundle(mock_valid_bundle, activate=True, strict_versions=False, session=db)
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
    register_model_bundle(mock_valid_bundle, activate=True, strict_versions=False, session=db)

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
    assert crit_machine.operational_status == "critical"
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

    with pytest.raises(ValueError, match="FATAL: Demo fleet seeding cannot proceed"):
        seed_demo_engines(bundle_dir, session=db)
