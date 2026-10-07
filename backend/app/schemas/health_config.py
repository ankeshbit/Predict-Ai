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


DEFAULT_HEALTH_BANDS: List[HealthBandInfo] = [
    HealthBandInfo(key="Excellent", label="Excellent (86–100)", min_score=86, max_score=100),
    HealthBandInfo(key="Healthy", label="Healthy (71–85)", min_score=71, max_score=85),
    HealthBandInfo(key="Warning", label="Warning (51–70)", min_score=51, max_score=70),
    HealthBandInfo(key="Poor", label="Poor (31–50)", min_score=31, max_score=50),
    HealthBandInfo(key="Critical", label="Critical (0–30)", min_score=0, max_score=30),
]


class HealthConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: str
    anomaly_weight: float
    data_quality_penalty: Dict[str, float]
    trend_enabled: bool
    is_active: bool
    created_at: datetime
    bands: List[HealthBandInfo] = Field(default_factory=lambda: list(DEFAULT_HEALTH_BANDS))


class HealthConfigUpdateRequest(BaseModel):
    anomaly_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    data_quality_penalty: Optional[Dict[str, float]] = None
    trend_enabled: Optional[bool] = None
