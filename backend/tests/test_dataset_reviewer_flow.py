"""
Integration tests for Reviewer Localhost Dataset Experience:
- Exhaustive dataset profiling
- Interactive schema remapping with confidence
- 3 sample files verification: PASS, WARN (OOD range comparison), FAIL (blocked scoring)
- Warning acknowledgment gate on scoring
- Compatibility report download (JSON & CSV)
- Live database dataset summary
- Selective demo reset with user data purging
"""

import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.dataset_profiler import profile_dataset_file
from app.services.importer import register_model_bundle

SAMPLE_DIR = (Path(__file__).resolve().parent.parent.parent / "database" / "sample_data").resolve()


def test_dataset_profiler_computes_exact_statistics():
    """Validates that dataset_profiler computes genuine, non-fabricated metrics."""
    compatible_path = SAMPLE_DIR / "compatible_fd001_slice.csv"
    assert compatible_path.exists(), f"Sample file missing: {compatible_path}"

    prof = profile_dataset_file(compatible_path, "compatible_fd001_slice.csv")
    assert prof["filename"] == "compatible_fd001_slice.csv"
    assert prof["total_rows"] == 60
    assert prof["total_columns"] == 26
    assert prof["has_header"] is True
    assert prof["duplicate_rows"] == 0
    assert "sensor_2" in prof["numeric_stats"]
    assert prof["numeric_stats"]["sensor_2"]["min"] > 600.0
    assert prof["unit_stats"] is not None
    assert prof["unit_stats"]["entity_count"] == 1
    assert prof["unit_stats"]["min_cycles_per_entity"] == 60


def test_schema_detection_confidence_and_remapping(client: TestClient, admin_headers: dict):
    """Tests auto-mapping confidence scoring and user remapping via PUT /datasets/{id}/mapping."""
    csv_content = (
        "unit,cycles,operating_setting_1,operating_setting_2,operating_setting_3,"
        + ",".join(f"s_{i}" for i in range(1, 22))
        + "\n"
        + "1,1,0.0,0.0,100.0,"
        + ",".join(str(500.0 + i) for i in range(1, 22))
        + "\n"
    )
    files = {"file": ("renamed_engine.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/v1/datasets/upload", files=files, headers=admin_headers)
    assert upload_res.status_code == 201
    data = upload_res.json()
    ds_id = data["id"]
    assert "profile" in data
    assert data["profile"]["total_rows"] == 1

    # Validate endpoint returns confidences
    val_res = client.post(f"/api/v1/datasets/{ds_id}/validate", headers=admin_headers)
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert "confidences" in val_data
    assert val_data["confidences"]["unit_id"] >= 0.8
    assert val_data["confidences"]["cycle"] >= 0.8

    # Remap a column
    curr_map = val_data["detected_mapping"]
    curr_map["unit_id"] = "unit"
    remap_res = client.put(f"/api/v1/datasets/{ds_id}/mapping", json={"mapping": curr_map}, headers=admin_headers)
    assert remap_res.status_code == 200
    remap_data = remap_res.json()
    assert remap_data["schema_mapping"]["unit_id"] == "unit"
    assert len(remap_data["schema_mapping_hash"]) == 64


def test_three_sample_datasets_compatibility_outcomes(
    client: TestClient, admin_headers: dict, mock_valid_bundle, db
):
    """Verifies expected outcomes for the 3 reviewer sample datasets: PASS, WARN (OOD), FAIL."""
    register_model_bundle(mock_valid_bundle, activate=True, session=db)

    # 1. Compatible slice -> PASS
    p1 = SAMPLE_DIR / "compatible_fd001_slice.csv"
    with open(p1, "rb") as f:
        up1 = client.post("/api/v1/datasets/upload", files={"file": ("compatible_slice.csv", f, "text/csv")}, headers=admin_headers)
    ds1_id = up1.json()["id"]

    chk1 = client.post(f"/api/v1/datasets/{ds1_id}/compatibility-check", headers=admin_headers)
    assert chk1.status_code == 200
    c1_data = chk1.json()
    assert c1_data["passed"] is True
    assert c1_data["failed_checks"] == 0
    assert c1_data["warning_checks"] == 0
    assert c1_data["has_warnings"] is False
    assert "meets all" in c1_data["summary_sentence"]

    # 2. Out of range warn slice -> WARN with OOD range comparison
    p2 = SAMPLE_DIR / "out_of_range_warn.csv"
    with open(p2, "rb") as f:
        up2 = client.post("/api/v1/datasets/upload", files={"file": ("ood_warn.csv", f, "text/csv")}, headers=admin_headers)
    ds2_id = up2.json()["id"]

    chk2 = client.post(f"/api/v1/datasets/{ds2_id}/compatibility-check", headers=admin_headers)
    assert chk2.status_code == 200
    c2_data = chk2.json()
    assert c2_data["passed"] is True
    assert c2_data["failed_checks"] == 0
    assert c2_data["warning_checks"] >= 1
    assert c2_data["has_warnings"] is True
    assert "sensor_2" in c2_data["ood_sensors"]
    assert "range_comparisons" in c2_data
    assert c2_data["range_comparisons"]["sensor_2"]["is_ood"] is True

    # 3. Non-FD001 dataset -> FAIL (409 Conflict with exact PRD message)
    p3 = SAMPLE_DIR / "incompatible_non_fd001.csv"
    with open(p3, "rb") as f:
        up3 = client.post("/api/v1/datasets/upload", files={"file": ("non_fd001.csv", f, "text/csv")}, headers=admin_headers)
    ds3_id = up3.json()["id"]

    chk3 = client.post(f"/api/v1/datasets/{ds3_id}/compatibility-check", headers=admin_headers)
    assert chk3.status_code == 409
    err = chk3.json()["error"]
    assert err["code"] == "DATASET_INCOMPATIBLE"
    assert err["message"] == "This dataset is not compatible with the selected model."
    assert "Why this model cannot be used" in err["details"]["plain_language_explanation"]

    # Incompatible dataset cannot be ingested
    ing_fail = client.post(f"/api/v1/datasets/{ds3_id}/ingest", headers=admin_headers)
    assert ing_fail.status_code == 409
    assert ing_fail.json()["error"]["code"] == "DATASET_INCOMPATIBLE"

    # Incompatible dataset cannot be scored
    score_fail = client.post("/api/v1/scoring-runs", json={"dataset_id": ds3_id}, headers=admin_headers)
    assert score_fail.status_code == 409
    assert score_fail.json()["error"]["code"] == "DATASET_INCOMPATIBLE"
    assert score_fail.json()["error"]["message"] == "This dataset is not compatible with the selected model."


def test_warning_acknowledgment_gate_on_scoring(
    client: TestClient, admin_headers: dict, mock_valid_bundle, db
):
    """Validates that a dataset with warnings blocks scoring until explicit acknowledgment."""
    register_model_bundle(mock_valid_bundle, activate=True, session=db)

    p2 = SAMPLE_DIR / "out_of_range_warn.csv"
    with open(p2, "rb") as f:
        up2 = client.post("/api/v1/datasets/upload", files={"file": ("ood_warn.csv", f, "text/csv")}, headers=admin_headers)
    ds2_id = up2.json()["id"]

    # Run check to establish warning status
    chk2 = client.post(f"/api/v1/datasets/{ds2_id}/compatibility-check", headers=admin_headers)
    assert chk2.status_code == 200

    # Ingest dataset
    ing_res = client.post(f"/api/v1/datasets/{ds2_id}/ingest", json={"acknowledged_warnings": True}, headers=admin_headers)
    assert ing_res.status_code == 200

    # Scoring without acknowledgment is blocked
    score_unack = client.post(
        "/api/v1/scoring-runs",
        json={"dataset_id": ds2_id, "acknowledged_warnings": False},
        headers=admin_headers,
    )
    assert score_unack.status_code == 409
    assert score_unack.json()["error"]["code"] == "WARNINGS_NOT_ACKNOWLEDGED"

    # Scoring with acknowledgment succeeds
    score_ack = client.post(
        "/api/v1/scoring-runs",
        json={"dataset_id": ds2_id, "acknowledged_warnings": True},
        headers=admin_headers,
    )
    assert score_ack.status_code == 202


def test_download_compatibility_report_json_and_csv(
    client: TestClient, admin_headers: dict, engineer_headers: dict, mock_valid_bundle, db
):
    """Verifies downloading the compatibility report as JSON and CSV."""
    register_model_bundle(mock_valid_bundle, activate=True, session=db)

    p1 = SAMPLE_DIR / "compatible_fd001_slice.csv"
    with open(p1, "rb") as f:
        up = client.post("/api/v1/datasets/upload", files={"file": ("report_test.csv", f, "text/csv")}, headers=admin_headers)
    ds_id = up.json()["id"]

    client.post(f"/api/v1/datasets/{ds_id}/compatibility-check", headers=admin_headers)

    # Download JSON
    res_json = client.get(f"/api/v1/datasets/{ds_id}/compatibility/download?format=json", headers=engineer_headers)
    assert res_json.status_code == 200
    assert res_json.headers["content-type"].startswith("application/json")
    json_data = res_json.json()
    assert "total_checks" in json_data
    assert "checks" in json_data

    # Download CSV
    res_csv = client.get(f"/api/v1/datasets/{ds_id}/compatibility/download?format=csv", headers=engineer_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    csv_text = res_csv.text
    assert "Check Number,Check Name,Status" in csv_text
    assert "Column Completeness" in csv_text


def test_demo_reset_with_clear_user_datasets(
    client: TestClient, admin_headers: dict, mock_valid_bundle, db
):
    """Tests reset preview and selective user dataset clearing."""
    register_model_bundle(mock_valid_bundle, activate=True, session=db)

    # Upload user dataset
    p1 = SAMPLE_DIR / "compatible_fd001_slice.csv"
    with open(p1, "rb") as f:
        up = client.post("/api/v1/datasets/upload", files={"file": ("user_slice.csv", f, "text/csv")}, headers=admin_headers)
    assert up.status_code == 201

    # Check reset preview
    prev = client.get("/api/v1/demo/reset/preview", headers=admin_headers)
    assert prev.status_code == 200
    prev_data = prev.json()
    assert prev_data["user_datasets_count"] >= 1

    # Reset demo without clearing user data
    res_keep = client.post("/api/v1/demo/reset?clear_user_datasets=false", headers=admin_headers)
    assert res_keep.status_code == 200
    assert res_keep.json()["cleared_user_datasets_count"] == 0

    # User dataset still exists
    prev_after = client.get("/api/v1/demo/reset/preview", headers=admin_headers)
    assert prev_after.json()["user_datasets_count"] >= 1

    # Reset demo clearing user data
    res_clear = client.post("/api/v1/demo/reset?clear_user_datasets=true", headers=admin_headers)
    assert res_clear.status_code == 200
    assert res_clear.json()["cleared_user_datasets_count"] >= 1

    # User datasets now 0
    prev_final = client.get("/api/v1/demo/reset/preview", headers=admin_headers)
    assert prev_final.json()["user_datasets_count"] == 0
