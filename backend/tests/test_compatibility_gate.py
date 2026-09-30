"""
Comprehensive integration tests for PRD FR-6 Dataset Compatibility Gate
Tests all 11 verification checks against compatible and incompatible datasets.
"""

from pathlib import Path
import uuid as uuid_lib
import numpy as np
import pandas as pd
import pytest
from app.adapters.cmapss_fd001 import CmapssFd001Adapter
from app.models.entities import Dataset
from app.services.compatibility import run_fr6_compatibility_checks

FIXTURES_DIR = Path("database/sample_data").resolve()


def _generate_valid_df(units=2, cycles=40):
    adapter = CmapssFd001Adapter()
    rows = []
    for u in range(1, units + 1):
        for c in range(1, cycles + 1):
            row = {"unit_id": u, "cycle": c, "op_setting_1": 0.0, "op_setting_2": 0.0, "op_setting_3": 100.0}
            for s in range(1, 22):
                if f"sensor_{s}" in [
                    "sensor_1", "sensor_5", "sensor_6", "sensor_10",
                    "sensor_16", "sensor_18", "sensor_19",
                ]:
                    row[f"sensor_{s}"] = float(s * 10)  # constant
                else:
                    row[f"sensor_{s}"] = float(s * 10) + c * 0.05  # varying
            rows.append(row)
    df = pd.DataFrame(rows)
    mapping = {col: col for col in adapter.canonical_columns}
    return df, mapping


def test_fr6_all_11_checks_pass_on_valid_data():
    df, mapping = _generate_valid_df(units=2, cycles=40)
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is True
    assert report.failed_checks == 0
    assert report.passed_checks == 11
    assert len(report.checks) == 11


def test_check_1_missing_canonical_columns():
    df, mapping = _generate_valid_df()
    del mapping["sensor_21"]  # Missing canonical column
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c1 = next(c for c in report.checks if c.check_number == 1)
    assert c1.status == "failed"
    assert "sensor_21" in c1.details["missing_columns"]


def test_check_2_non_numeric_channel():
    df, mapping = _generate_valid_df()
    df["sensor_3"] = ["corrupted_text" if i == 5 else str(v) for i, v in enumerate(df["sensor_3"])]
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c2 = next(c for c in report.checks if c.check_number == 2)
    assert c2.status == "failed"
    assert "sensor_3" in c2.details["non_numeric_columns"]


def test_check_3_sequence_length_less_than_30():
    df, mapping = _generate_valid_df(units=1, cycles=15)  # 15 < 30
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c3 = next(c for c in report.checks if c.check_number == 3)
    assert c3.status == "failed"
    assert "Sequence Length" in c3.check_name


def test_check_4_non_monotonic_cycles():
    df, mapping = _generate_valid_df(units=1, cycles=40)
    # Introduce cycle reversal
    df.loc[10, "cycle"] = 5
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c4 = next(c for c in report.checks if c.check_number == 4)
    assert c4.status == "failed"
    assert "Monotonic Cycle Ordering" in c4.check_name


def test_check_5_duplicate_timestamps():
    df, mapping = _generate_valid_df(units=1, cycles=40)
    # Duplicate row 5
    dup_row = df.iloc[[5]]
    df = pd.concat([df, dup_row], ignore_index=True)
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c5 = next(c for c in report.checks if c.check_number == 5)
    assert c5.status == "failed"
    assert c5.details["duplicate_count"] == 1


def test_check_6_excessive_missing_values():
    df, mapping = _generate_valid_df(units=1, cycles=40)
    # Set 20% of sensor_4 to NaN
    df.loc[:8, "sensor_4"] = np.nan
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c6 = next(c for c in report.checks if c.check_number == 6)
    assert c6.status == "failed"
    assert "sensor_4" in c6.details["bad_missing_columns"]


def test_check_7_infinite_value_outlier():
    df, mapping = _generate_valid_df(units=1, cycles=40)
    df.loc[5, "sensor_2"] = np.inf
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c7 = next(c for c in report.checks if c.check_number == 7)
    assert c7.status == "failed"
    assert "sensor_2" in c7.details["outlier_columns"]


def test_check_8_constant_column_varying():
    df, mapping = _generate_valid_df(units=1, cycles=40)
    # sensor_1 is constant in FD001, make it vary widely
    df["sensor_1"] = np.linspace(100, 200, len(df))
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c8 = next(c for c in report.checks if c.check_number == 8)
    assert c8.status == "failed"
    assert "sensor_1" in c8.details["varying_constant_channels"]


def test_check_10_zero_units():
    df, mapping = _generate_valid_df(units=0, cycles=0)
    report = run_fr6_compatibility_checks(df, mapping)

    assert report.passed is False
    c10 = next(c for c in report.checks if c.check_number == 10)
    assert c10.status == "failed"


# -------------------------------------------------------------
# End-to-End API Tests with Sample Fixtures
# -------------------------------------------------------------
def test_api_compatible_fd001_passes_gate(client, admin_headers, db):
    fixture_path = FIXTURES_DIR / "compatible_fd001_synthetic_test_fixture.csv"
    assert fixture_path.exists(), f"Missing test fixture: {fixture_path}"

    with open(fixture_path, "rb") as f:
        upload_res = client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            files={"file": (fixture_path.name, f, "text/csv")},
            data={"name": "FD001 Compatible Benchmark"},
        )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    # Validate mapping
    val_res = client.post(f"/api/v1/datasets/{dataset_id}/validate", headers=admin_headers)
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # Run compatibility check
    comp_res = client.post(f"/api/v1/datasets/{dataset_id}/compatibility-check", headers=admin_headers)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["passed"] is True
    assert comp_data["failed_checks"] == 0
    assert comp_data["passed_checks"] == 11

    # Verify dataset status in DB
    dataset = db.get(Dataset, uuid_lib.UUID(dataset_id))
    assert dataset.status == "valid"


def test_api_incompatible_ai4i_rejected_409(client, admin_headers, db):
    fixture_path = FIXTURES_DIR / "incompatible_ai4i_synthetic_test_fixture.csv"
    assert fixture_path.exists(), f"Missing test fixture: {fixture_path}"

    with open(fixture_path, "rb") as f:
        upload_res = client.post(
            "/api/v1/datasets/upload",
            headers=admin_headers,
            files={"file": (fixture_path.name, f, "text/csv")},
            data={"name": "AI4I Incompatible Dataset"},
        )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    # Compatibility check must return 409 Conflict with DATASET_INCOMPATIBLE
    comp_res = client.post(f"/api/v1/datasets/{dataset_id}/compatibility-check", headers=admin_headers)
    assert comp_res.status_code == 409
    error_body = comp_res.json()
    assert error_body["error"]["code"] == "DATASET_INCOMPATIBLE"
    assert error_body["error"]["message"] == "This dataset is not compatible with the selected model."

    # Must contain actionable Expected/Found/How-to-fix table in details
    details = error_body["error"]["details"]
    assert details["passed"] is False
    assert details["failed_checks"] > 0
    assert "checks" in details

    # First check must be failed Column Completeness
    c1 = details["checks"][0]
    assert c1["check_name"] == "Column Completeness"
    assert c1["status"] == "failed"
    assert "expected_value" in c1
    assert "found_value" in c1
    assert "how_to_fix" in c1

    # Verify dataset status marked 'rejected_incompatible' in DB
    dataset = db.get(Dataset, uuid_lib.UUID(dataset_id))
    assert dataset.status == "rejected_incompatible"
