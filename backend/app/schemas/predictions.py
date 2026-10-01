"""
Pydantic schemas for scored predictions, breakdown points, and lineage.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class PredictionLineageResponse(BaseModel):
    dataset_version: str
    schema_mapping_hash: str
    feature_config_version: str
    preprocessing_version: str
    failure_model_version_id: uuid.UUID
    anomaly_model_version_id: Optional[uuid.UUID] = None
    health_config_id: uuid.UUID
    horizon: int
    horizon_unit: str
    as_of_index: int
    predicted_at: datetime
    input_window_start: int
    input_window_end: int


class AdditiveBreakdownResponse(BaseModel):
    start: float = 100.0
    failure_risk_points: float
    anomaly_points: float
    data_quality_points: float
    trend_points: Optional[float] = None
    trend_status: str = "not_enabled"
    clipping_adjustment_points: float = 0.0
    health_indicator: float


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    cycle: int
    as_of_index: int
    predicted_at: datetime
    failure_probability: float
    risk_level: str
    health_indicator: float
    health_band: str
    penalty_risk: float
    penalty_anomaly: float
    penalty_dq: float
    penalty_trend: float
    clipping_adjustment: float
    breakdown: Optional[AdditiveBreakdownResponse] = None
    lineage: Optional[PredictionLineageResponse] = None
    reliability_flags: Dict[str, Any]


class PredictionListResponse(BaseModel):
    items: List[PredictionResponse]
    total: int


class FeatureContribution(BaseModel):
    feature: str
    value: float
    contribution: float
    direction: str


class ExplanationResponse(BaseModel):
    method: str
    space: str
    top_features: List[FeatureContribution]
