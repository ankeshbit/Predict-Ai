"""
Model Governance & Registry API router: bundle versions, model cards, and Colab evaluation results.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import ModelEvaluation, ModelVersion, User
from app.schemas.models import ModelEvaluationResponse, ModelVersionResponse

router = APIRouter(prefix="/models", tags=["Models & Registry"])


@router.get("", response_model=List[ModelVersionResponse])
def list_models(
    task: Optional[str] = Query(None, description="Filter by task: failure_risk or anomaly"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Lists registered model versions from the model registry."""
    stmt = select(ModelVersion)
    if task:
        stmt = stmt.where(ModelVersion.task == task)
    if is_active is not None:
        stmt = stmt.where(ModelVersion.is_active == is_active)

    models = db.scalars(stmt.order_by(ModelVersion.created_at.desc())).all()
    return [ModelVersionResponse.model_validate(m) for m in models]


@router.get("/active", response_model=List[ModelVersionResponse])
def get_active_models(
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves currently active production model bundles."""
    stmt = select(ModelVersion).where(ModelVersion.is_active.is_(True))
    models = db.scalars(stmt).all()
    return [ModelVersionResponse.model_validate(m) for m in models]


@router.get("/{model_id}", response_model=ModelVersionResponse)
def get_model(
    model_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves model card and version metadata for a registered model."""
    model = db.get(ModelVersion, model_id)
    if not model:
        raise NotFoundError(message=f"Model version {model_id} not found")
    return ModelVersionResponse.model_validate(model)


@router.get("/{model_id}/evaluation", response_model=ModelEvaluationResponse)
def get_model_evaluation(
    model_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves stored Colab evaluation metrics, downsampled curves, and feature importances.

    PRD Rule: Zero fabricated literals. If no evaluation record exists, display "Model evaluation not available."
    """
    model = db.get(ModelVersion, model_id)
    if not model:
        raise NotFoundError(message=f"Model version {model_id} not found")

    evaluation = db.scalar(
        select(ModelEvaluation).where(ModelEvaluation.model_version_id == model_id)
    )
    if not evaluation:
        raise NotFoundError(message="Model evaluation not available.")

    return ModelEvaluationResponse.model_validate(evaluation)
