"""
Pytest fixtures and test database harness for backend tests.
Uses an isolated PostgreSQL database running on localhost or via TEST_DATABASE_URL.
Migrations are applied via Alembic (no create_all).
Tables are cleanly truncated between tests.
"""

import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config

from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.entities import HealthIndicatorConfig, User

# Ensure fast timeout in tests so DB connection attempts don't stall
os.environ.setdefault("DB_CONNECT_TIMEOUT", "2")

# Database URL for tests - points to PostgreSQL 16
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    settings.DATABASE_URL or "postgresql+psycopg://postgres:postgrespassword@localhost:5432/predict_ai_test",
)

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

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


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    """Ensure database schema is up-to-date with Alembic migrations before running any tests."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="function")
def db():
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
    # Seed default health config
    health_cfg = HealthIndicatorConfig(
        id=uuid.uuid4(),
        version="1.0",
        weight_risk=50.0,
        weight_anomaly=30.0,
        weight_trend=20.0,
        trend_window=20,
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
