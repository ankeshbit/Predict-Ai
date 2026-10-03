"""
Upload and Staging Service
Enforces strict file security, content-sniffing, CSV injection protection,
and staging expiration per PRD FR-5 and §16.
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

from app.core.errors import AppError, StagingExpiredError
from fastapi import UploadFile

# Upload limits
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_UPLOAD_ROWS = 250_000
STAGING_EXPIRY_SECONDS = 3600  # 1 hour TTL

STAGING_DIR = Path(__file__).resolve().parent.parent.parent / "staging_uploads"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# Disallowed binary magic byte prefixes
BINARY_MAGIC_PREFIXES = [
    b"MZ",                # Windows PE EXE / DLL
    b"\x7fELF",           # Linux ELF
    b"PK\x03\x04",        # ZIP / Office OpenXML / JAR
    b"%PDF",              # PDF
    b"\x1f\x8b",          # GZIP
    b"\xca\xfe\xba\xbe",  # Mach-O / Java Class
    b"\x89PNG",           # PNG
    b"\xff\xd8\xff",      # JPEG
    b"GIF8",              # GIF
]


def sanitize_csv_cell(cell: str) -> str:
    """
    Sanitizes string cells against CSV injection.
    Neutralizes formula execution in spreadsheet software (=, @, or +/ - followed by text/symbols).
    Preserves legitimate negative/positive numbers (e.g., -0.002, +42).
    """
    if not cell or not isinstance(cell, str):
        return cell

    stripped = cell.strip()
    if not stripped:
        return cell

    first_char = stripped[0]
    # Check for direct formula prefixes
    if first_char in ["=", "@"]:
        return "'" + cell

    # Check for +/- followed by non-digits/non-decimal (e.g. -cmd or +cmd)
    if first_char in ["+", "-"]:
        if len(stripped) > 1 and not (stripped[1].isdigit() or stripped[1] == "."):
            return "'" + cell

    return cell


def validate_file_content(head_bytes: bytes) -> None:
    """
    Sniffs content headers and byte distributions to verify plain text / CSV.
    Rejects binaries, executables, and non-UTF8 data.
    """
    if not head_bytes:
        raise AppError(
            status_code=400,
            code="EMPTY_FILE",
            message="Uploaded file is empty.",
        )

    # Check magic prefixes
    for magic in BINARY_MAGIC_PREFIXES:
        if head_bytes.startswith(magic):
            raise AppError(
                status_code=400,
                code="INVALID_FILE_TYPE",
                message="Uploaded file contains disallowed binary or executable headers. Only CSV/text is permitted.",
            )

    # Check for null bytes (indicators of binary data)
    if b"\x00" in head_bytes:
        raise AppError(
            status_code=400,
            code="INVALID_FILE_TYPE",
            message="Uploaded file contains binary null bytes. Only UTF-8 text/CSV is permitted.",
        )

    # Verify UTF-8 decodability
    try:
        head_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise AppError(
            status_code=400,
            code="ENCODING_ERROR",
            message="Uploaded file is not valid UTF-8 encoded text.",
        )


def stage_uploaded_file(upload_file: UploadFile) -> Tuple[str, Dict[str, Any]]:
    """
    Streams and validates uploaded file to secure staging directory.
    Enforces maximum size limit, computes SHA-256 hash, and counts rows.
    Returns:
        staging_filename: Random UUID hex filename
        metadata: Dict with file_size_bytes, sha256_hash, row_count
    """
    random_filename = f"{uuid.uuid4().hex}.csv"
    destination_path = STAGING_DIR / random_filename

    sha256 = hashlib.sha256()
    total_bytes = 0
    row_count = 0
    first_chunk = True

    try:
        with open(destination_path, "wb") as f_out:
            while True:
                chunk = upload_file.file.read(64 * 1024)
                if not chunk:
                    break

                if first_chunk:
                    validate_file_content(chunk[:1024])
                    first_chunk = False

                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise AppError(
                        status_code=413,
                        code="PAYLOAD_TOO_LARGE",
                        message=f"Uploaded file exceeds maximum limit of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
                    )

                sha256.update(chunk)
                row_count += chunk.count(b"\n")
                f_out.write(chunk)

            if first_chunk:
                validate_file_content(b"")

    except Exception:
        destination_path.unlink(missing_ok=True)
        raise

    if row_count > MAX_UPLOAD_ROWS:
        destination_path.unlink(missing_ok=True)
        raise AppError(
            status_code=400,
            code="MAX_ROWS_EXCEEDED",
            message=f"Uploaded file exceeds maximum row limit of {MAX_UPLOAD_ROWS:,} rows (found {row_count:,}).",
        )

    # row_count counts newlines; subtract 1 for the header row (data rows only)
    data_row_count = max(0, row_count - 1)

    metadata = {
        "file_size_bytes": total_bytes,
        "sha256_hash": sha256.hexdigest(),
        "row_count": data_row_count,
        "staging_path": str(destination_path),
        "staged_at": datetime.now(timezone.utc).isoformat(),
    }

    return random_filename, metadata


def get_staged_file_path(staging_filename: str) -> Path:
    """
    Resolves staged file path and verifies that the 1-hour TTL has not expired.
    Raises StagingExpiredError (HTTP 410) if expired or missing.
    """
    # Prevent directory traversal
    safe_name = os.path.basename(staging_filename)
    file_path = STAGING_DIR / safe_name

    if not file_path.exists():
        raise StagingExpiredError(
            message="Staged upload file not found or has been expired and deleted."
        )

    # Check 1-hour TTL
    mtime = file_path.stat().st_mtime
    age_seconds = datetime.now().timestamp() - mtime
    if age_seconds > STAGING_EXPIRY_SECONDS:
        # Delete expired file
        file_path.unlink(missing_ok=True)
        raise StagingExpiredError(
            message=f"Staging upload has expired ({int(age_seconds)}s > {STAGING_EXPIRY_SECONDS}s TTL). Please re-upload."
        )

    return file_path
