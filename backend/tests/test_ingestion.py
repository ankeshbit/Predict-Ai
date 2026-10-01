"""
Unit and integration tests for dataset ingestion background service and job polling
"""

import uuid as uuid_lib
from pathlib import Path

from app.models.entities import Machine, SensorReading
from app.services.ingestion import run_ingestion_job

FIXTURES_DIR = (Path(__file__).resolve().parent.parent.parent / "database" / "sample_data").resolve()


def test_ingestion_lifecycle_and_job_polling(client, admin_headers, engineer_headers, db):
    fixture_path = FIXTURES_DIR / "compatible_fd001_synthetic_test_fixture.csv"
    assert fixture_path.exists()

    # 1. Upload
    with open(fixture_path, "rb") as f:
        up_res = client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            files={"file": (fixture_path.name, f, "text/csv")},
            data={"name": "Ingestion Fleet Test"},
        )
    assert up_res.status_code == 201
    dataset_id_str = up_res.json()["id"]
    dataset_id = uuid_lib.UUID(dataset_id_str)

    # 2. Validate
    val_res = client.post(f"/api/v1/datasets/{dataset_id_str}/validate", headers=admin_headers)
    assert val_res.status_code == 200

    # 3. Compatibility check
    comp_res = client.post(f"/api/v1/datasets/{dataset_id_str}/compatibility-check", headers=admin_headers)
    assert comp_res.status_code == 200

    # 4. Trigger Ingestion via API
    ingest_res = client.post(f"/api/v1/datasets/{dataset_id_str}/ingest", headers=admin_headers)
    assert ingest_res.status_code == 200
    job_id_str = ingest_res.json()["job_id"]
    job_id = uuid_lib.UUID(job_id_str)

    # Run ingestion worker synchronously using the test session for deterministic verification
    db.expire_all()  # refresh any cached objects
    run_ingestion_job(job_id, dataset_id, _db=db)

    # 5. Poll Job status via /jobs/{id}
    job_res = client.get(f"/api/v1/jobs/{job_id_str}", headers=engineer_headers)
    assert job_res.status_code == 200
    job_data = job_res.json()
    assert job_data["status"] == "completed", f"Job failed: {job_data}"
    assert job_data["progress_pct"] == 100.0
    assert job_data["result"]["rows_ingested"] == 200  # 5 units × 40 cycles
    assert job_data["result"]["units_ingested"] == 5

    # 6. Verify Machines created in DB
    machines = db.query(Machine).filter_by(dataset_id=dataset_id).all()
    assert len(machines) == 5
    codes = [m.machine_code for m in machines]
    assert any("u001" in c for c in codes)
    assert any("u005" in c for c in codes)

    # 7. Verify SensorReadings created in DB for machine u001
    m1 = next(m for m in machines if "u001" in m.machine_code)
    readings = db.query(SensorReading).filter_by(machine_id=m1.id).order_by(SensorReading.cycle.asc()).all()
    assert len(readings) == 40
    assert readings[0].cycle == 1
    assert readings[-1].cycle == 40
    assert readings[0].sensor_2 is not None


def test_cannot_ingest_incompatible_dataset(client, admin_headers, db):
    fixture_path = FIXTURES_DIR / "incompatible_ai4i_synthetic_test_fixture.csv"
    with open(fixture_path, "rb") as f:
        up_res = client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            files={"file": (fixture_path.name, f, "text/csv")},
            data={"name": "Incompatible Run"},
        )
    assert up_res.status_code == 201
    dataset_id = up_res.json()["id"]

    # Run compatibility check (will fail and set rejected_incompatible)
    client.post(f"/api/v1/datasets/{dataset_id}/compatibility-check", headers=admin_headers)

    # Attempt to ingest
    ingest_res = client.post(f"/api/v1/datasets/{dataset_id}/ingest", headers=admin_headers)
    assert ingest_res.status_code == 409
    assert ingest_res.json()["error"]["code"] == "DATASET_INCOMPATIBLE"
