"""
Pydantic schemas for Model Versions, Model Governance, and Colab Evaluations.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bundle_version: str
    task: str
    model_type: str
    adapter_key: str
    feature_config_version: str
    preprocessing_version: str
    input_features: List[str]
    horizon: Optional[int] = None
    horizon_unit: Optional[str] = None
    decision_threshold: Optional[float] = None
    is_active: bool
    model_card_complete: bool
    sha256_hash: str
    python_version: str
    created_at: datetime


class ModelEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    task: str
    metrics: Dict[str, Any]
    confusion_matrix: Dict[str, Any]
    calibration_curve: Dict[str, Any]
    curves: Dict[str, Any]
    feature_importance: List[Dict[str, Any]]
    methodology: str
    limitations: List[str]
    evaluated_at: datetime
