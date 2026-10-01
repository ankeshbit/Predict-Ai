"""
Pydantic schemas for Anomalies and Anomaly Episodes.
PRD §14.4
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    cycle: int
    prediction_id: Optional[uuid.UUID] = None
    anomaly_score: float
    severity: str
    is_anomaly: bool
    episode_id: Optional[uuid.UUID] = None
    affected_features: Optional[List[Dict[str, Any]]] = None
    detected_at: datetime


class AnomalyListResponse(BaseModel):
    items: List[AnomalyResponse]
    total: int
