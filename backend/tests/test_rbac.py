"""
Unit and integration tests for Role-Based Access Control (RBAC).
Verifies strict enforcement of Admin vs Engineer privileges, and confirms
that machine status cannot be directly patched (workflow side effects only).
"""

import uuid

from app.models.entities import Dataset, Machine


def test_no_direct_patch_machine_status(client, admin_headers, engineer_headers, db):
    """PRD requirement: No direct PATCH machine status; operational status transitions

    occur exclusively via maintenance workflow side effects.
    """
    machine = Machine(
        id=uuid.uuid4(),
        machine_code="test-unit-no-patch",
        operational_status="active",
        health_band="Healthy",
        health_indicator=80.0,
        is_demo=False,
    )
    db.add(machine)
    db.commit()

    # Neither engineer nor admin can PATCH machine status directly
    res_eng = client.patch(
        f"/api/v1/machines/{machine.id}/status",
        headers=engineer_headers,
        json={"operational_status": "maintenance"},
    )
    assert res_eng.status_code in (404, 405)

    res_adm = client.patch(
        f"/api/v1/machines/{machine.id}/status",
        headers=admin_headers,
        json={"operational_status": "maintenance"},
    )
    assert res_adm.status_code in (404, 405)


def test_engineer_cannot_trigger_dataset_ingestion(client, engineer_headers, admin_headers, db):
    """Admin-only actions (like dataset upload / ingest) must reject engineer with 403 FORBIDDEN."""
    ds = Dataset(
        id=uuid.uuid4(),
        name="RBAC Ingest Test",
        slug="rbac-ingest-test",
        status="valid",
        schema_mapping={"unit_id": "unit_id", "cycle": "cycle"},
    )
    db.add(ds)
    db.commit()

    res = client.post(
        f"/api/v1/datasets/{ds.id}/ingest",
        headers=engineer_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
