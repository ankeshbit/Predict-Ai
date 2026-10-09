"""
Scoring Runs API Router (PRD §14.4)
Executes asynchronous batch scoring runs on compatible datasets.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.core.errors import ConflictError, DatasetIncompatibleError, NotFoundError
from app.models.entities import Dataset, DatasetCompatibilityCheck, Job, ModelVersion, User
from app.schemas.scoring import ScoringRunRequest, ScoringRunResponse
from app.services.scoring_service import run_scoring_job

router = APIRouter(prefix="/scoring-runs", tags=["Scoring Runs"])
legacy_scoring_router = APIRouter(prefix="/scoring", tags=["Scoring Runs"])


@router.post("", response_model=ScoringRunResponse, status_code=202)
@legacy_scoring_router.post("/run", response_model=ScoringRunResponse, status_code=202)
def create_scoring_run(
    payload: ScoringRunRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Triggers an asynchronous scoring run job across machines for a compatible dataset (Admin only).
    Rejects incompatible datasets with HTTP 409 DATASET_INCOMPATIBLE.
    Rejects if no active failure risk model is registered.
    """
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset:
        raise NotFoundError(message=f"Dataset with id {payload.dataset_id} not found")

    if dataset.status == "rejected_incompatible":
        raise DatasetIncompatibleError(
            message="This dataset is not compatible with the selected model.",
            details={"dataset_id": str(dataset.id), "status": dataset.status},
        )

    # Check if dataset has out-of-distribution warnings requiring explicit acknowledgment
    chk = db.scalar(
        select(DatasetCompatibilityCheck)
        .where(DatasetCompatibilityCheck.dataset_id == dataset.id)
        .order_by(DatasetCompatibilityCheck.checked_at.desc())
        .limit(1)
    )
    if chk and chk.status == "warning" and not payload.acknowledged_warnings:
        raise ConflictError(
            code="WARNINGS_NOT_ACKNOWLEDGED",
            message="This dataset contains out-of-distribution warnings that must be acknowledged before scoring.",
            details=chk.report,
        )

    # Verify active model exists
    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == dataset.adapter_key,
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    if not active_model:
        raise ConflictError(
            code="NO_ACTIVE_MODEL",
            message="No active failure risk model is registered for this adapter.",
        )

    # Create Job record
    job = Job(
        id=uuid.uuid4(),
        job_type="scoring_run",
        status="queued",
        progress_pct=0.0,
        input_params={
            "dataset_id": str(payload.dataset_id),
            "machine_ids": [str(m) for m in payload.machine_ids] if payload.machine_ids else [],
            "model_version_id": str(active_model.id),
            "acknowledged_warnings": payload.acknowledged_warnings,
        },
        created_by_user_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Queue background task
    background_tasks.add_task(
        run_scoring_job,
        job_id=job.id,
        dataset_id=dataset.id,
        machine_ids=payload.machine_ids,
        acknowledged_warnings=payload.acknowledged_warnings,
    )

    return ScoringRunResponse(
        job_id=job.id,
        status="queued",
        message="Scoring run has been queued successfully.",
    )
