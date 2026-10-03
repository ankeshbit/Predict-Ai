"""
Tests for system health check endpoint
"""

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["version"] == "3.0.0"
    assert "database" in data
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_health_check_with_no_active_model(client, db):
    """The app must start and /health must work with no active model."""
    from app.models.entities import ModelVersion
    from sqlalchemy import select

    active_count = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
    assert active_count is None, "Precondition: No active model should exist in this test"

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "healthy"]
    assert data["database"] == "connected"

