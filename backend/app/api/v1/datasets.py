"""
Datasets API router: upload, validation, FR-6 compatibility checks, and ingestion.
"""

import re
import uuid
from typing import Optional

import pandas as pd
from app.adapters.cmapss_fd001 import CmapssFd001Adapter
from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import ConflictError, DatasetIncompatibleError, NotFoundError
from app.models.entities import Dataset, DatasetCompatibilityCheck, Job, User
from app.schemas.datasets import (
    CompatibilityCheckResponse,
    DatasetListResponse,
    DatasetResponse,
    DatasetUploadResponse,
    IngestDatasetResponse,
    ValidateDatasetResponse,
)
from app.services.compatibility import run_fr6_compatibility_checks
from app.services.ingestion import run_ingestion_job
from app.services.upload import get_staged_file_path, stage_uploaded_file
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/datasets", tags=["Datasets"])


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


@router.post("", response_model=DatasetUploadResponse, status_code=201)
@router.post("/upload", response_model=DatasetUploadResponse, status_code=201)
def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Uploads a telemetry CSV file to secure staging.
    Enforces file size limit, content-sniffing, and UTF-8 verification (Admin only).
    """
    dataset_name = name.strip() if name and name.strip() else (file.filename or "Uploaded Dataset")
    staging_filename, metadata = stage_uploaded_file(file)

    base_slug = _slugify(dataset_name)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    dataset = Dataset(
        id=uuid.uuid4(),
        name=dataset_name,
        slug=slug,
        filename=file.filename or staging_filename,
        file_size_bytes=metadata["file_size_bytes"],
        row_count=metadata["row_count"],
        staging_filename=staging_filename,
        status="uploaded",
        created_by_user_id=current_user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return DatasetUploadResponse(
        id=dataset.id,
        name=dataset.name,
        slug=dataset.slug,
        filename=dataset.filename,
        file_size_bytes=dataset.file_size_bytes,
        row_count=dataset.row_count,
        status=dataset.status,
        staging_filename=staging_filename,
        created_at=dataset.created_at,
    )


@router.get("", response_model=DatasetListResponse)
def list_datasets(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists all datasets with pagination."""
    stmt = select(Dataset)
    if status_filter:
        stmt = stmt.where(Dataset.status == status_filter)
    stmt = stmt.order_by(Dataset.created_at.desc()).offset(offset).limit(limit)

    items = db.scalars(stmt).all()
    total = db.query(Dataset).count()

    return DatasetListResponse(
        items=[DatasetResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves single dataset metadata by ID."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")
    return DatasetResponse.model_validate(dataset)


@router.post("/{dataset_id}/validate", response_model=ValidateDatasetResponse)
def validate_dataset(
    dataset_id: uuid.UUID,
    adapter_key: str = Query("cmapss_fd001", description="Adapter schema key"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Validates staged dataset structure, auto-detects column mapping, and computes mapping hash (Admin only).
    """
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    staged_path = get_staged_file_path(dataset.staging_filename)

    # Read CSV header / first chunk
    try:
        df = pd.read_csv(staged_path, nrows=100)
        if df.shape[1] == 1:
            df = pd.read_csv(staged_path, sep=r"\s+", nrows=100, header=None)
            # Create synthetic column names col_0..col_N if headerless
            df.columns = [f"col_{i}" for i in range(df.shape[1])]
    except Exception:
        df = pd.read_csv(staged_path, sep=r"\s+", nrows=100, header=None)
        df.columns = [f"col_{i}" for i in range(df.shape[1])]

    adapter = CmapssFd001Adapter()
    raw_cols = [str(c) for c in df.columns]

    # If headerless 26-column format, map sequentially
    if len(raw_cols) == 26 and all(c.startswith("col_") for c in raw_cols):
        detected_mapping = {canon: raw_cols[i] for i, canon in enumerate(adapter.canonical_columns)}
        unmapped = []
    else:
        detected_mapping, unmapped = adapter.detect_mapping(raw_cols)

    mapping_hash = adapter.compute_mapping_hash(detected_mapping)
    is_valid = len(unmapped) == 0

    dataset.schema_mapping = detected_mapping
    dataset.schema_mapping_hash = mapping_hash
    dataset.status = "valid" if is_valid else "invalid"
    db.commit()
    db.refresh(dataset)

    return ValidateDatasetResponse(
        dataset_id=dataset.id,
        adapter_key=adapter_key,
        is_valid=is_valid,
        detected_mapping=detected_mapping,
        unmapped_columns=unmapped,
        schema_mapping_hash=mapping_hash,
        row_count=dataset.row_count or 0,
    )


@router.post("/{dataset_id}/compatibility-check", response_model=CompatibilityCheckResponse)
def check_dataset_compatibility(
    dataset_id: uuid.UUID,
    adapter_key: str = Query("cmapss_fd001", description="Adapter schema key"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Executes the 11 PRD FR-6 Dataset Compatibility Gate checks against the staged file.
    If compatible, returns 200 OK.
    If incompatible, sets status to 'rejected_incompatible' and returns 409 Conflict (DATASET_INCOMPATIBLE).
    """
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    staged_path = get_staged_file_path(dataset.staging_filename)

    # Read CSV
    try:
        df = pd.read_csv(staged_path)
        if df.shape[1] == 1:
            df = pd.read_csv(staged_path, sep=r"\s+", header=None)
            df.columns = [f"col_{i}" for i in range(df.shape[1])]
    except Exception:
        df = pd.read_csv(staged_path, sep=r"\s+", header=None)
        df.columns = [f"col_{i}" for i in range(df.shape[1])]

    # Use existing mapping or auto-detect
    mapping = dataset.schema_mapping
    adapter = CmapssFd001Adapter()
    if not mapping:
        raw_cols = [str(c) for c in df.columns]
        if len(raw_cols) == 26 and all(c.startswith("col_") for c in raw_cols):
            mapping = {canon: raw_cols[i] for i, canon in enumerate(adapter.canonical_columns)}
        else:
            mapping, _ = adapter.detect_mapping(raw_cols)
        dataset.schema_mapping = mapping
        dataset.schema_mapping_hash = adapter.compute_mapping_hash(mapping)

    # Execute all 11 FR-6 checks
    report = run_fr6_compatibility_checks(df, mapping, adapter_key)

    # Delete previous compatibility checks for this dataset
    db.query(DatasetCompatibilityCheck).filter_by(dataset_id=dataset.id).delete()

    # Save check result as one row with complete report JSONB (PRD §13)
    chk_entity = DatasetCompatibilityCheck(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        status="passed" if report.passed else "failed",
        report=report.to_dict(),
    )
    db.add(chk_entity)

    if not report.passed:
        dataset.status = "rejected_incompatible"
        dataset.error_message = f"Failed {report.failed_checks} of 11 compatibility checks."
        db.commit()

        # Raise 409 DATASET_INCOMPATIBLE with Expected/Found/How-to-fix table
        raise DatasetIncompatibleError(
            message="This dataset is not compatible with the selected model.",
            details=report.to_dict(),
        )

    # Passed
    dataset.status = "valid"
    dataset.error_message = None
    db.commit()

    return CompatibilityCheckResponse(
        dataset_id=dataset.id,
        passed=True,
        total_checks=report.total_checks,
        passed_checks=report.passed_checks,
        failed_checks=report.failed_checks,
        checks=report.to_dict()["checks"],
    )


@router.get("/{dataset_id}/compatibility", response_model=CompatibilityCheckResponse)
def get_dataset_compatibility(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves the latest PRD FR-6 compatibility check report for a dataset (PRD §14.3)."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    check = db.scalar(
        select(DatasetCompatibilityCheck)
        .where(DatasetCompatibilityCheck.dataset_id == dataset_id)
        .order_by(DatasetCompatibilityCheck.checked_at.desc())
        .limit(1)
    )
    if not check:
        raise NotFoundError(message=f"No compatibility checks found for dataset {dataset_id}")

    rep = check.report
    return CompatibilityCheckResponse(
        dataset_id=dataset.id,
        passed=check.status == "passed",
        total_checks=rep.get("total_checks", len(rep.get("checks", []))),
        passed_checks=rep.get("passed_checks", 0),
        failed_checks=rep.get("failed_checks", 0),
        checks=rep.get("checks", []),
    )


@router.post("/{dataset_id}/ingest", response_model=IngestDatasetResponse)
def ingest_dataset(
    dataset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Triggers asynchronous ingestion of a validated, compatible dataset (Admin only).
    """
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    if dataset.status == "rejected_incompatible":
        raise ConflictError(
            code="DATASET_INCOMPATIBLE",
            message="Cannot ingest an incompatible dataset. Please resolve compatibility gate failures.",
        )

    if not dataset.schema_mapping:
        raise ConflictError(
            code="DATASET_NOT_VALIDATED",
            message="Dataset must be validated before ingestion.",
        )

    # Create Job record
    job = Job(
        id=uuid.uuid4(),
        job_type="data_ingestion",
        status="queued",
        progress_pct=0.0,
        input_params={"dataset_id": str(dataset.id), "dataset_name": dataset.name},
        created_by_user_id=current_user.id,
    )
    db.add(job)
    dataset.status = "ingesting"
    db.commit()
    db.refresh(job)

    # Launch background task
    background_tasks.add_task(run_ingestion_job, job.id, dataset.id)

    return IngestDatasetResponse(
        job_id=job.id,
        dataset_id=dataset.id,
        status="queued",
        message="Data ingestion job has been queued successfully.",
    )
