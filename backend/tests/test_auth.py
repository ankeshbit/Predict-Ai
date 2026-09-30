"""
Unit and integration tests for authentication endpoints (/api/v1/auth/*) and Argon2id hashing.
"""

from app.core.security import verify_password
from app.models.entities import AuditLog, User


def test_login_success(client, db):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@predicore.io", "password": "AdminSecret123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@predicore.io"
    assert data["user"]["role"] == "admin"

    # Verify audit log recorded
    audit = db.query(AuditLog).filter_by(action="auth.login_success").first()
    assert audit is not None
    assert audit.resource_type == "user"


def test_login_invalid_password(client, db):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@predicore.io", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"

    # Verify failed login audit log
    audit = db.query(AuditLog).filter_by(action="auth.login_failed").first()
    assert audit is not None


def test_login_nonexistent_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@predicore.io", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_deactivated_user(client, db):
    user = db.query(User).filter_by(email="engineer@predicore.io").first()
    user.is_active = False
    db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "engineer@predicore.io", "password": "EngineerSecret123!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_endpoint_authenticated(client, engineer_headers):
    response = client.get("/api/v1/auth/me", headers=engineer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "engineer@predicore.io"
    assert data["role"] == "engineer"


def test_me_endpoint_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_change_password_success(client, engineer_headers, db):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=engineer_headers,
        json={
            "current_password": "EngineerSecret123!",
            "new_password": "NewSecretPassword456!",
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"

    # Verify new password in DB
    user = db.query(User).filter_by(email="engineer@predicore.io").first()
    assert verify_password("NewSecretPassword456!", user.password_hash)


def test_change_password_invalid_current(client, engineer_headers):
    response = client.post(
        "/api/v1/auth/change-password",
        headers=engineer_headers,
        json={
            "current_password": "IncorrectPassword123!",
            "new_password": "NewSecretPassword456!",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
