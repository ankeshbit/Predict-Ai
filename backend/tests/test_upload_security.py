"""
Unit and integration tests for upload security, content sniffing, and CSV sanitization
"""

import io
import time

import pytest

from app.core.errors import AppError, StagingExpiredError
from app.services.upload import (
    STAGING_DIR,
    get_staged_file_path,
    sanitize_csv_cell,
    validate_file_content,
)


def test_sanitize_csv_cell():
    # Direct formula injection
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("@SUM(A1:B10)") == "'@SUM(A1:B10)"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-cmd|' /C calc'!A0") == "'-cmd|' /C calc'!A0"

    # Legitimate numbers should NOT be prepended with quote
    assert sanitize_csv_cell("-0.0002") == "-0.0002"
    assert sanitize_csv_cell("+42.5") == "+42.5"
    assert sanitize_csv_cell("123") == "123"
    assert sanitize_csv_cell("normal_text") == "normal_text"


def test_validate_file_content_rejects_binaries():
    # Windows executable
    with pytest.raises(AppError) as exc_info:
        validate_file_content(b"MZ\x90\x00\x03\x00\x00\x00")
    assert exc_info.value.code == "INVALID_FILE_TYPE"

    # ELF binary
    with pytest.raises(AppError) as exc_info:
        validate_file_content(b"\x7fELF\x02\x01\x01\x00")
    assert exc_info.value.code == "INVALID_FILE_TYPE"

    # ZIP archive
    with pytest.raises(AppError) as exc_info:
        validate_file_content(b"PK\x03\x04\x14\x00\x00\x00")
    assert exc_info.value.code == "INVALID_FILE_TYPE"

    # PDF document
    with pytest.raises(AppError) as exc_info:
        validate_file_content(b"%PDF-1.4\n%...")
    assert exc_info.value.code == "INVALID_FILE_TYPE"

    # Binary null bytes
    with pytest.raises(AppError) as exc_info:
        validate_file_content(b"unit,cycle\x00\x01\x02")
    assert exc_info.value.code == "INVALID_FILE_TYPE"

    # Empty file
    with pytest.raises(AppError) as exc_info:
        validate_file_content(b"")
    assert exc_info.value.code == "EMPTY_FILE"


def test_upload_endpoint_success(client, admin_headers):
    csv_content = b"unit_id,cycle,op_setting_1,op_setting_2,op_setting_3\n1,1,0.0,0.0,100.0\n"
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        files={"file": ("test_upload.csv", io.BytesIO(csv_content), "text/csv")},
        data={"name": "Test Engine Upload"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Engine Upload"
    assert data["status"] == "uploaded"
    assert data["row_count"] == 1
    assert "staging_filename" in data


def test_upload_endpoint_rejects_binary(client, admin_headers):
    fake_exe = b"MZ\x90\x00" + b"\x00" * 100
    response = client.post(
        "/api/v1/datasets/upload",
        headers=admin_headers,
        files={"file": ("malicious.exe", io.BytesIO(fake_exe), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_upload_endpoint_engineer_forbidden(client, engineer_headers):
    csv_content = b"unit_id,cycle\n1,1\n"
    response = client.post(
        "/api/v1/datasets/upload",
        headers=engineer_headers,
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_staging_ttl_expiry(tmp_path):
    test_file = STAGING_DIR / "expired_test.csv"
    test_file.write_text("unit_id,cycle\n1,1\n")

    # Set file mtime to 2 hours ago (7200 seconds)
    two_hours_ago = time.time() - 7200
    import os
    os.utime(test_file, (two_hours_ago, two_hours_ago))

    with pytest.raises(StagingExpiredError):
        get_staged_file_path("expired_test.csv")
