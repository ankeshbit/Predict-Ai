"""
Datasets API router: upload, validation, FR-6 compatibility checks, remapping, profiling, and ingestion.
"""

import csv
import io
import json
import re
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.cmapss_fd001 import CmapssFd001Adapter
from app.core.auth import get_current_admin, get_current_engineer
from app.core.db import get_db
from app.core.errors import ConflictError, DatasetIncompatibleError, NotFoundError
from app.models.entities import (
    Alert,
    Dataset,
    DatasetCompatibilityCheck,
    Job,
    Machine,
    ModelVersion,
    Prediction,
    SensorReading,
    User,
)
from app.schemas.datasets import (
    CompatibilityCheckResponse,
    DatasetListResponse,
    DatasetProfileResponse,
    DatasetResponse,
    DatasetSummaryResponse,
    DatasetUploadResponse,
    IngestDatasetRequest,
    IngestDatasetResponse,
    UpdateMappingRequest,
    UpdateMappingResponse,
    ValidateDatasetResponse,
)
from app.services.compatibility import run_fr6_compatibility_checks
from app.services.dataset_profiler import profile_dataset_file
from app.services.ingestion import run_ingestion_job
from app.services.upload import get_staged_file_path, stage_uploaded_file

router = APIRouter(prefix="/datasets", tags=["Datasets"])

DEFAULT_FD001_FEATURE_RANGES = {
    "operating_setting_1": {"min": -0.0087, "max": 0.0087},
    "operating_setting_2": {"min": -0.0006, "max": 0.0006},
    "sensor_2": {"min": 641.21, "max": 644.53},
    "sensor_3": {"min": 1571.06, "max": 1616.91},
    "sensor_4": {"min": 1385.19, "max": 1441.49},
    "sensor_7": {"min": 549.85, "max": 555.86},
    "sensor_8": {"min": 2387.9, "max": 2388.56},
    "sensor_9": {"min": 9023.85, "max": 9244.59},
    "sensor_11": {"min": 46.85, "max": 48.52},
    "sensor_12": {"min": 518.69, "max": 523.38},
    "sensor_13": {"min": 2387.88, "max": 2388.56},
    "sensor_14": {"min": 8099.94, "max": 8293.72},
    "sensor_15": {"min": 8.3358, "max": 8.5848},
    "sensor_17": {"min": 388.0, "max": 399.0},
    "sensor_20": {"min": 38.14, "max": 39.41},
    "sensor_21": {"min": 22.8942, "max": 23.6184},
}


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
    Computes genuine dataset profile immediately and auto-detects column mappings (Admin only).
    """
    dataset_name = name.strip() if name and name.strip() else (file.filename or "Uploaded Dataset")
    staging_filename, metadata = stage_uploaded_file(file)

    base_slug = _slugify(dataset_name)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    staged_path = get_staged_file_path(staging_filename)
    prof = profile_dataset_file(staged_path, file.filename or staging_filename)

    # Auto-detect initial mapping and hash from detected columns
    adapter = CmapssFd001Adapter()
    col_names = prof["column_names"]
    mapping, unmapped, _confidences = adapter.detect_mapping_with_confidence(col_names)
    mapping_hash = adapter.compute_mapping_hash(mapping)

    dataset = Dataset(
        id=uuid.uuid4(),
        name=dataset_name,
        slug=slug,
        filename=file.filename or staging_filename,
        file_size_bytes=metadata["file_size_bytes"],
        row_count=prof["total_rows"],
        unit_count=prof["unit_stats"]["entity_count"] if prof.get("unit_stats") else None,
        schema_mapping=mapping,
        schema_mapping_hash=mapping_hash,
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
        filename=dataset.filename or staging_filename,
        file_size_bytes=dataset.file_size_bytes or 0,
        row_count=dataset.row_count or 0,
        status=dataset.status,
        staging_filename=staging_filename,
        created_at=dataset.created_at,
        profile=prof,
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


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Computes and returns exhaustive descriptive profile from the staged file."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    staged_path = get_staged_file_path(dataset.staging_filename)
    prof = profile_dataset_file(staged_path, dataset.filename or dataset.name)
    return DatasetProfileResponse(**prof)


@router.post("/{dataset_id}/validate", response_model=ValidateDatasetResponse)
def validate_dataset(
    dataset_id: uuid.UUID,
    adapter_key: str = Query("cmapss_fd001", description="Adapter schema key"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Validates staged dataset structure, auto-detects column mapping with confidence, and computes mapping hash (Admin only).
    """
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    staged_path = get_staged_file_path(dataset.staging_filename)
    prof = profile_dataset_file(staged_path, dataset.filename or dataset.name)

    adapter = CmapssFd001Adapter()
    col_names = prof["column_names"]

    detected_mapping, unmapped, confidences = adapter.detect_mapping_with_confidence(col_names)
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
        confidences=confidences,
        unmapped_columns=unmapped,
        schema_mapping_hash=mapping_hash,
        row_count=dataset.row_count or 0,
        profile=prof,
    )


@router.put("/{dataset_id}/mapping", response_model=UpdateMappingResponse)
def update_dataset_mapping(
    dataset_id: uuid.UUID,
    payload: UpdateMappingRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Allows user to manually correct column mappings and immediately recalculates the schema mapping hash.
    """
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    adapter = CmapssFd001Adapter()
    mapping = payload.mapping
    mapping_hash = adapter.compute_mapping_hash(mapping)
    unmapped = [c for c in adapter.canonical_columns if c not in mapping]
    is_valid = len(unmapped) == 0

    dataset.schema_mapping = mapping
    dataset.schema_mapping_hash = mapping_hash
    db.commit()
    db.refresh(dataset)

    return UpdateMappingResponse(
        dataset_id=dataset.id,
        schema_mapping=mapping,
        schema_mapping_hash=mapping_hash,
        is_valid=is_valid,
        unmapped_columns=unmapped,
    )


@router.post("/{dataset_id}/compatibility", response_model=CompatibilityCheckResponse)
@router.post("/{dataset_id}/compatibility-check", response_model=CompatibilityCheckResponse)
def check_dataset_compatibility(
    dataset_id: uuid.UUID,
    adapter_key: str = Query("cmapss_fd001", description="Adapter schema key"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Executes all 11 PRD FR-6 Dataset Compatibility Gate checks against the staged file.
    Evaluates value ranges against offline training ranges stored in the active model bundle.
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

    # Resolve training ranges from active model bundle if available
    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == dataset.adapter_key,
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    feature_ranges = None
    if active_model and active_model.artifact_path:
        schema_file = Path(active_model.artifact_path) / "metadata" / "schema.json"
        if schema_file.exists():
            try:
                with open(schema_file, "r", encoding="utf-8") as sf:
                    s_data = json.load(sf)
                    feature_ranges = s_data.get("feature_ranges")
            except Exception:
                pass
    if feature_ranges is None:
        feature_ranges = DEFAULT_FD001_FEATURE_RANGES

    # Execute all 11 FR-6 checks
    report = run_fr6_compatibility_checks(df, mapping, adapter_key, feature_ranges=feature_ranges)

    # Delete previous compatibility checks for this dataset
    db.query(DatasetCompatibilityCheck).filter_by(dataset_id=dataset.id).delete()

    chk_status = (
        "passed"
        if (report.passed and not report.has_warnings)
        else ("warning" if (report.passed and report.has_warnings) else "failed")
    )

    chk_entity = DatasetCompatibilityCheck(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        model_version_id=active_model.id if active_model else None,
        status=chk_status,
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

    # Passed or passed with warnings
    dataset.status = "valid"
    dataset.error_message = None
    db.commit()

    return CompatibilityCheckResponse(
        dataset_id=dataset.id,
        passed=True,
        total_checks=report.total_checks,
        passed_checks=report.passed_checks,
        failed_checks=report.failed_checks,
        warning_checks=report.warning_checks,
        has_warnings=report.has_warnings,
        summary_sentence=report.summary_sentence,
        plain_language_explanation=report.plain_language_explanation,
        ood_sensors=report.ood_sensors,
        range_comparisons=report.range_comparisons,
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
        passed=check.status in ["passed", "warning"],
        total_checks=rep.get("total_checks", len(rep.get("checks", []))),
        passed_checks=rep.get("passed_checks", 0),
        failed_checks=rep.get("failed_checks", 0),
        warning_checks=rep.get("warning_checks", 0),
        has_warnings=rep.get("has_warnings", False),
        summary_sentence=rep.get("summary_sentence"),
        plain_language_explanation=rep.get("plain_language_explanation"),
        ood_sensors=rep.get("ood_sensors"),
        range_comparisons=rep.get("range_comparisons"),
        checks=rep.get("checks", []),
    )


@router.get("/{dataset_id}/compatibility/download")
def download_compatibility_report(
    dataset_id: uuid.UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Downloads compatibility report in CSV or JSON format for reviewer audits."""
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
        raise NotFoundError(message=f"No compatibility check record found for dataset {dataset_id}")

    report = check.report
    if format == "json":
        content = json.dumps(report, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="compatibility_report_{dataset.slug}.json"'},
        )
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Check Number", "Check Name", "Status", "Expected Value", "Found Value", "How To Fix"])
        for c in report.get("checks", []):
            writer.writerow([
                c.get("check_number"),
                c.get("check_name"),
                c.get("status"),
                c.get("expected_value"),
                c.get("found_value"),
                c.get("how_to_fix"),
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="compatibility_report_{dataset.slug}.csv"'},
        )


@router.get("/{dataset_id}/summary", response_model=DatasetSummaryResponse)
def get_dataset_summary(
    dataset_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Returns database-queried totals for ingested units, readings, scored items, and opened alerts."""
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {dataset_id} not found")

    units_count = db.scalar(select(func.count(Machine.id)).where(Machine.dataset_id == dataset.id)) or 0
    readings_count = db.scalar(select(func.count(SensorReading.id)).where(SensorReading.dataset_id == dataset.id)) or 0
    scored_count = db.scalar(
        select(func.count(Prediction.id))
        .join(Machine, Prediction.machine_id == Machine.id)
        .where(Machine.dataset_id == dataset.id)
    ) or 0
    alerts_count = db.scalar(
        select(func.count(Alert.id))
        .join(Machine, Alert.machine_id == Machine.id)
        .where(Machine.dataset_id == dataset.id)
    ) or 0

    return DatasetSummaryResponse(
        dataset_id=dataset.id,
        units_count=units_count,
        readings_count=readings_count,
        scored_count=scored_count,
        alerts_count=alerts_count,
    )


@router.post("/{dataset_id}/ingest", response_model=IngestDatasetResponse)
def ingest_dataset(
    dataset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    payload: Optional[IngestDatasetRequest] = None,
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

    acknowledged = bool(payload and payload.acknowledged_warnings)

    # Create Job record
    job = Job(
        id=uuid.uuid4(),
        job_type="data_ingestion",
        status="queued",
        progress_pct=0.0,
        input_params={
            "dataset_id": str(dataset.id),
            "dataset_name": dataset.name,
            "acknowledged_warnings": acknowledged,
        },
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
