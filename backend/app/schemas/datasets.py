"""
Pydantic schemas for Dataset entities, upload, validation, and compatibility checks.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class DatasetProfileResponse(BaseModel):
    filename: str
    total_rows: int
    total_columns: int
    detected_delimiter: str
    raw_delimiter: Optional[str] = None
    has_header: bool
    column_names: List[str]
    duplicate_rows: int
    missing_counts: Dict[str, int]
    numeric_stats: Dict[str, Dict[str, float]]
    unit_stats: Optional[Dict[str, Any]] = None


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    filename: Optional[str] = None
    file_size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    unit_count: Optional[int] = None
    schema_mapping: Optional[Dict[str, str]] = None
    schema_mapping_hash: Optional[str] = None
    data_origin: Optional[str] = None
    is_demo: bool = False
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
    profile: Optional[Dict[str, Any]] = None


class ValidateDatasetResponse(BaseModel):
    dataset_id: uuid.UUID
    adapter_key: str
    is_valid: bool
    detected_mapping: Dict[str, str]
    confidences: Optional[Dict[str, float]] = None
    unmapped_columns: List[str]
    schema_mapping_hash: str
    row_count: int
    profile: Optional[Dict[str, Any]] = None


class UpdateMappingRequest(BaseModel):
    mapping: Dict[str, str]


class UpdateMappingResponse(BaseModel):
    dataset_id: uuid.UUID
    schema_mapping: Dict[str, str]
    schema_mapping_hash: str
    is_valid: bool
    unmapped_columns: List[str]


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
    warning_checks: int = 0
    has_warnings: bool = False
    summary_sentence: Optional[str] = None
    plain_language_explanation: Optional[str] = None
    ood_sensors: Optional[List[str]] = None
    range_comparisons: Optional[Dict[str, Any]] = None
    checks: List[CheckItem]


class IngestDatasetRequest(BaseModel):
    acknowledged_warnings: bool = False


class IngestDatasetResponse(BaseModel):
    job_id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    message: str


class DatasetSummaryResponse(BaseModel):
    dataset_id: uuid.UUID
    units_count: int
    readings_count: int
    scored_count: int
    alerts_count: int

