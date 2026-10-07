"""
Pydantic schemas for Machine Health Indicator configuration.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthBandInfo(BaseModel):
    key: str
    label: str
    min_score: int
    max_score: int


class HealthConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: str
    anomaly_weight: float
    data_quality_penalty: Dict[str, float]
    trend_enabled: bool
    is_active: bool
    created_at: datetime
    bands: List[HealthBandInfo] = Field(default_factory=list)


class HealthConfigUpdateRequest(BaseModel):
    anomaly_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    data_quality_penalty: Optional[Dict[str, float]] = None
    trend_enabled: Optional[bool] = None
    bands: Optional[List[HealthBandInfo]] = None
