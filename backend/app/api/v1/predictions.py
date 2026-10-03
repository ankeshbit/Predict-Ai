"""
Predictions & Explainability API Router (PRD §14.4)
"""

import uuid
from typing import List, Optional

from app.core.auth import get_current_engineer
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.entities import Machine, Prediction, User
from app.schemas.predictions import (
    AdditiveBreakdownResponse,
    ExplanationResponse,
    PredictionLineageResponse,
    PredictionResponse,
)
from app.services.explanation_service import compute_prediction_explanation
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(tags=["Predictions & Explainability"])


def _to_prediction_response(p: Prediction) -> PredictionResponse:
    lineage = PredictionLineageResponse(
        dataset_version=p.dataset_version,
        schema_mapping_hash=p.schema_mapping_hash,
        feature_config_version=p.feature_config_version,
        preprocessing_version=p.preprocessing_version,
        failure_model_version_id=p.failure_model_version_id,
        anomaly_model_version_id=p.anomaly_model_version_id,
        health_config_id=p.health_config_id,
        horizon=p.horizon,
        horizon_unit=p.horizon_unit,
        as_of_index=p.as_of_index,
        predicted_at=p.predicted_at,
        input_window_start=p.input_window_start,
        input_window_end=p.input_window_end,
    )
    breakdown = AdditiveBreakdownResponse(
        start=100.0,
        failure_risk_points=p.penalty_risk,
        anomaly_points=p.penalty_anomaly,
        data_quality_points=p.penalty_dq,
        trend_points=None,
        trend_status="not_enabled",
        clipping_adjustment_points=p.clipping_adjustment,
        health_indicator=p.health_indicator,
    )
    return PredictionResponse(
        id=p.id,
        machine_id=p.machine_id,
        cycle=p.cycle,
        as_of_index=p.as_of_index,
        predicted_at=p.predicted_at,
        failure_probability=p.failure_probability,
        risk_level=p.risk_level,
        health_indicator=p.health_indicator,
        health_band=p.health_band,
        penalty_risk=p.penalty_risk,
        penalty_anomaly=p.penalty_anomaly,
        penalty_dq=p.penalty_dq,
        penalty_trend=p.penalty_trend,
        clipping_adjustment=p.clipping_adjustment,
        breakdown=breakdown,
        lineage=lineage,
        reliability_flags=p.reliability_flags or {},
    )


@router.get("/predictions", response_model=List[PredictionResponse])
def list_predictions(
    machine_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves list of predictions across machines with lineage and breakdown points."""
    stmt = select(Prediction)
    if machine_id:
        stmt = stmt.where(Prediction.machine_id == machine_id)
    preds = db.scalars(
        stmt.order_by(Prediction.predicted_at.desc(), Prediction.cycle.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [_to_prediction_response(p) for p in preds]


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
def get_prediction(
    prediction_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves a single prediction with complete lineage object and breakdown points."""
    pred = db.get(Prediction, prediction_id)
    if not pred:
        raise NotFoundError(message=f"Prediction with id {prediction_id} not found")
    return _to_prediction_response(pred)


@router.get("/predictions/{prediction_id}/explanation", response_model=ExplanationResponse)
def get_prediction_explanation(
    prediction_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves feature contributions, trend facts, and explanation text for a prediction."""
    return compute_prediction_explanation(prediction_id, db)


@router.get("/machines/{machine_id}/predictions/latest", response_model=PredictionResponse)
def get_latest_machine_prediction(
    machine_id: uuid.UUID,
    current_user: User = Depends(get_current_engineer),
    db: Session = Depends(get_db),
):
    """Retrieves the latest scored prediction for a machine."""
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine {machine_id} not found")

    latest_pred = db.scalar(
        select(Prediction)
        .where(Prediction.machine_id == machine_id)
        .order_by(Prediction.cycle.desc())
        .limit(1)
    )
    if not latest_pred:
        raise NotFoundError(
            code="NOT_SCORED",
            message=f"Machine {machine_id} has not been scored yet.",
        )
    return _to_prediction_response(latest_pred)
