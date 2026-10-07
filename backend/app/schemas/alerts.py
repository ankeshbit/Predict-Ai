"""
Pydantic schemas for Alerts and Human-in-the-Loop notifications.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    alert_type: str
    status: str
    severity: str
    trigger_cycle: int
    trigger_score: float
    recommendation_text: str
    recommendation_rule_id: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by_user_id: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime


class AlertListResponse(BaseModel):
    items: List[AlertResponse]
    total: int


class AlertAcknowledgeRequest(BaseModel):
    note: Optional[str] = None


class AlertResolveRequest(BaseModel):
    resolution_type: str = Field(..., min_length=1, description="Required resolution classification")
    resolution_note: Optional[str] = None
