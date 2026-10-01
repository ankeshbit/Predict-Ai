"""
Pydantic schemas for Dataset entities, upload, validation, and compatibility checks.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    filename: str
    file_size_bytes: int
    row_count: Optional[int] = None
    unit_count: Optional[int] = None
    schema_mapping: Optional[Dict[str, str]] = None
    schema_mapping_hash: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    items: List[DatasetResponse]
    total: int


class DatasetUploadResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    filename: str
    file_size_bytes: int
    row_count: int
    status: str
    staging_filename: str
    created_at: datetime


class ValidateDatasetResponse(BaseModel):
    dataset_id: uuid.UUID
    adapter_key: str
    is_valid: bool
    detected_mapping: Dict[str, str]
    unmapped_columns: List[str]
    schema_mapping_hash: str
    row_count: int


class CheckItem(BaseModel):
    check_number: int
    check_name: str
    status: str
    expected_value: str
    found_value: str
    how_to_fix: str
    details: Optional[Dict[str, Any]] = None


class CompatibilityCheckResponse(BaseModel):
    dataset_id: uuid.UUID
    passed: bool
    total_checks: int
    passed_checks: int
    failed_checks: int
    checks: List[CheckItem]


class IngestDatasetResponse(BaseModel):
    job_id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    message: str
