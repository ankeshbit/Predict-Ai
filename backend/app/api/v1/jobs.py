"""
Jobs API router: status polling for background tasks
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import Job, User
from app.schemas.jobs import JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """
    Polls status and progress of an asynchronous background job.
    """
    job = db.get(Job, job_id)
    if not job:
        raise NotFoundError(message=f"Job with id {job_id} not found")
    return JobResponse.model_validate(job)
