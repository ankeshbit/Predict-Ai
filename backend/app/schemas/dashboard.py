"""
Pydantic schemas for Fleet Dashboard analytics and KPI summaries.
PRD §14.7
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_machines: int
    healthy_count: int
    warning_count: int
    critical_count: int
    average_health_indicator: float
    open_alerts_count: int
    dataset_banner_text: str
    dataset_badge_text: str
    # Granular counts for frontend distribution chart
    health_band_counts: dict  # e.g. {"Excellent": 2, "Healthy": 1, ...}
    operational_counts: dict  # e.g. {"active": 7, "maintenance": 1, "archived": 0}
    active_count: int
    maintenance_count: int
    server_time: Optional[datetime] = None


class PriorityMachineItem(BaseModel):
    id: uuid.UUID
    machine_code: str
    operational_status: str
    health_indicator: float
    health_band: str
    failure_probability: float
    horizon: int
    horizon_unit: str
    risk_level: str
    as_of_cycle: int


class RecentAnomalyItem(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_code: str
    cycle: int
    severity: str
    anomaly_score: float
    is_anomaly: bool
    detected_at: datetime


class RecentAlertItem(BaseModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    machine_code: str
    alert_type: str
    status: str
    severity: str
    trigger_cycle: int
    trigger_score: float
    recommendation_text: str
    created_at: datetime


class ProbabilityDistributionBin(BaseModel):
    bin_range: str
    min_prob: float
    max_prob: float
    count: int


class ProbabilityDistributionResponse(BaseModel):
    bins: List[ProbabilityDistributionBin]
    total_scored_machines: int
