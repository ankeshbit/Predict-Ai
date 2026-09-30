"""
Unit and integration tests for Role-Based Access Control (RBAC).
Verifies strict enforcement of Admin vs Engineer privileges.
"""

import uuid

from app.models.entities import Machine


def test_engineer_cannot_modify_machine_status(client, engineer_headers, db):
    # Create test machine
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="test-unit-01",
        operational_status="active",
        health_band="healthy",
        health_indicator=80.0,
        is_demo=False,
    )
    db.add(machine)
    db.commit()

    # Engineer attempts PATCH /machines/{id}/status
    response = client.patch(
        f"/api/v1/machines/{machine.id}/status",
        headers=engineer_headers,
        json={"operational_status": "maintenance"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"


def test_admin_can_modify_machine_status(client, admin_headers, db):
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="test-unit-02",
        operational_status="active",
        health_band="healthy",
        health_indicator=85.0,
        is_demo=False,
    )
    db.add(machine)
    db.commit()

    response = client.patch(
        f"/api/v1/machines/{machine.id}/status",
        headers=admin_headers,
        json={"operational_status": "maintenance"},
    )
    assert response.status_code == 200
    assert response.json()["operational_status"] == "maintenance"

    # Verify updated in DB
    refreshed = db.query(Machine).filter_by(id=machine.id).first()
    assert refreshed.operational_status == "maintenance"
