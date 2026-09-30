"""
Pytest fixtures and test database harness for backend tests.
Uses an isolated in-memory SQLite database with StaticPool.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure fast timeout in tests so DB connection attempts don't stall
os.environ.setdefault("DB_CONNECT_TIMEOUT", "1")

from app.core.db import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.entities import HealthIndicatorConfig, User

# Test in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Creates a fresh database schema for every test function."""
    Base.metadata.create_all(bind=test_engine)
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
    Base.metadata.drop_all(bind=test_engine)


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
