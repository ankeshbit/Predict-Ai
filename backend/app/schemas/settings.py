"""
Pydantic schemas for Settings and Admin Audit Logs.
PRD §14.8
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class RiskBandsConfig(BaseModel):
    low_max: float = 0.10  # Aligned with decision_threshold (0.10): at/above threshold is at least Medium
    medium_max: float = 0.50
    high_max: float = 0.80


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_id: str
    alert_type: str
    failure_probability_threshold: float
    anomaly_severity_threshold: str
    consecutive_cycles: int
    is_active: bool


class AlertRuleUpdateRequest(BaseModel):
    failure_probability_threshold: Optional[float] = None
    anomaly_severity_threshold: Optional[str] = None
    consecutive_cycles: Optional[int] = None
    is_active: Optional[bool] = None


class ReliabilityConfigResponse(BaseModel):
    max_missing_fraction: float
    max_out_of_range_fraction: float
    max_z_shift: float
    min_window_length: int
    description: str


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
