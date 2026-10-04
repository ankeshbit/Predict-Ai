"""
Pytest fixtures and test database harness for backend tests.
Uses an isolated PostgreSQL database running on localhost or via TEST_DATABASE_URL.
Migrations are applied via Alembic (no create_all).
Tables are cleanly truncated between tests.
"""

import json
import os

os.environ["TESTING"] = "1"
# Ensure fast timeout in tests so DB connection attempts don't stall
os.environ.setdefault("DB_CONNECT_TIMEOUT", "2")

# Database URL for tests - strictly isolated from dev database
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai_test",
)

# Safety guard: NEVER point TEST_DATABASE_URL at Neon
if "neon.tech" in TEST_DATABASE_URL or "neon.tech" in os.environ.get("DATABASE_URL", ""):
    raise RuntimeError(
        "CRITICAL SAFETY GUARD: TEST_DATABASE_URL or DATABASE_URL points to a Neon database (*.neon.tech)! "
        "Tests must run ONLY against throwaway local Postgres (e.g. docker-compose). "
        "Running test suites against Neon is strictly forbidden per AGENTS.md to prevent data corruption."
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL_DIRECT"] = TEST_DATABASE_URL

import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.core import db as core_db
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.entities import HealthIndicatorConfig, User

settings.DATABASE_URL = TEST_DATABASE_URL
settings.DATABASE_URL_DIRECT = TEST_DATABASE_URL

test_connect_args = {"prepare_threshold": None}
local_hosts = ("localhost", "127.0.0.1", "test-postgres", "postgres", "predict_ai_test_postgres")
if not any(h in TEST_DATABASE_URL for h in local_hosts):
    test_connect_args["sslmode"] = "require"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args=test_connect_args,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Rebind app SessionLocal to test_engine during tests to prevent leaking into dev DB
core_db.engine = test_engine
core_db.SessionLocal = TestingSessionLocal

ALL_TABLES = [
    "audit_log",
    "jobs",
    "settings",
    "alert_rules",
    "maintenance_records",
    "alerts",
    "anomalies",
    "predictions",
    "health_indicator_configs",
    "model_evaluations",
    "model_versions",
    "sensor_readings",
    "machines",
    "dataset_compatibility_checks",
    "datasets",
    "users",
]


@pytest.fixture(scope="session")
def apply_migrations():
    """Ensure database schema is up-to-date with Alembic migrations before running any tests."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="function")
def db(apply_migrations):
    """Provides a clean database session for each test function, seeded with default admin/engineer/health_config."""
    with test_engine.connect() as conn:
        truncate_sql = f"TRUNCATE TABLE {', '.join(ALL_TABLES)} RESTART IDENTITY CASCADE;"
        conn.execute(text(truncate_sql))
        conn.commit()

    session = TestingSessionLocal()

    # Seed initial test users
    admin = User(
        id=uuid.uuid4(),
        email="admin@predicore.io",
        password_hash=get_password_hash("AdminSecret123!"),
        role="admin",
        is_active=True,
    )
    engineer = User(
        id=uuid.uuid4(),
        email="engineer@predicore.io",
        password_hash=get_password_hash("EngineerSecret123!"),
        role="engineer",
        is_active=True,
    )
    # Seed default health config (notebook configuration: anomaly_weight, data_quality_penalty, trend not enabled)
    health_cfg = HealthIndicatorConfig(
        id=uuid.uuid4(),
        version="1.0",
        anomaly_weight=0.30,
        data_quality_penalty={"DATA_OK": 0.0, "DATA_WARNING": 10.0},
        trend_enabled=False,
        is_active=True,
    )

    session.add(admin)
    session.add(engineer)
    session.add(health_cfg)
    session.commit()

    yield session

    session.close()


@pytest.fixture(scope="function")
def client(db):
    """TestClient with get_db dependency overridden to use the test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(db):
    admin = db.query(User).filter_by(email="admin@predicore.io").first()
    token = create_access_token(data={"sub": str(admin.id), "role": admin.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def engineer_headers(db):
    engineer = db.query(User).filter_by(email="engineer@predicore.io").first()
    token = create_access_token(data={"sub": str(engineer.id), "role": engineer.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_valid_bundle(tmp_path):
    """Creates a temporary valid bundle structure matching production layout."""
    import hashlib
    bundle_dir = tmp_path / "cmapss-fd001-h30-test"
    bundle_dir.mkdir()
    (bundle_dir / "metadata").mkdir()
    (bundle_dir / "evaluation").mkdir()
    (bundle_dir / "demo").mkdir()
    (bundle_dir / "model").mkdir()
    (bundle_dir / "preprocessing").mkdir()

    # Model and preprocessor files
    (bundle_dir / "model" / "calibrated_failure_model.joblib").write_bytes(b"dummy_model_bytes")
    (bundle_dir / "model" / "anomaly_detector.joblib").write_bytes(b"dummy_anomaly_bytes")
    (bundle_dir / "preprocessing" / "feature_engineer.joblib").write_bytes(b"dummy_fe_bytes")
    (bundle_dir / "preprocessing" / "imputer.joblib").write_bytes(b"dummy_imputer_bytes")

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
            "calibration": {"brier_calibrated": 0.04, "ece_calibrated": 0.015},
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
