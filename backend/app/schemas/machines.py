"""
Pydantic schemas for Machine entities and telemetry history
PRD §13, §14.2
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class MachineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: Optional[uuid.UUID] = None
    dataset_name: Optional[str] = None
    machine_code: str
    name: Optional[str] = None
    machine_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    install_date: Optional[datetime] = None
    source_unit_id: Optional[int] = None
    operational_status: str
    health_indicator: Optional[float] = None
    health_band: Optional[str] = None
    is_demo: bool = False
    demo_cluster: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Latest prediction enrichment (populated by list/get endpoints)
    failure_probability: Optional[float] = None
    risk_level: Optional[str] = None
    current_cycle: Optional[int] = None
    anomaly_score: Optional[float] = None
    anomaly_severity: Optional[float] = None
    is_anomaly: Optional[bool] = None
    anomaly_threshold: Optional[float] = None
    reliability_status: Optional[str] = None
    prediction_horizon: Optional[int] = None
    prediction_horizon_unit: Optional[str] = None
    schema_mapping_hash: Optional[str] = None
    feature_config_version: Optional[str] = None
    preprocessing_version: Optional[str] = None
    failure_model_version_id: Optional[str] = None
    anomaly_model_version_id: Optional[str] = None
    penalty_risk: Optional[float] = None
    penalty_anomaly: Optional[float] = None
    penalty_dq: Optional[float] = None
    penalty_trend: Optional[float] = None
    rule_id: Optional[str] = None
    recommendation_text: Optional[str] = None


class MachineCreateRequest(BaseModel):
    machine_code: str
    name: Optional[str] = None
    machine_type: Optional[str] = "Turbofan Engine"
    location: Optional[str] = None
    notes: Optional[str] = None
    install_date: Optional[datetime] = None
    dataset_id: Optional[uuid.UUID] = None
    source_unit_id: Optional[int] = None


class MachineUpdateRequest(BaseModel):
    name: Optional[str] = None
    machine_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class MachineArchiveRequest(BaseModel):
    force: bool = False


class MachineTimelineItem(BaseModel):
    id: uuid.UUID
    event_type: str  # 'anomaly', 'alert', 'maintenance'
    cycle: Optional[int] = None
    timestamp: datetime
    title: str
    severity: Optional[str] = None
    status: Optional[str] = None
    details: Dict[str, Any] = {}


class MachineTimelineResponse(BaseModel):
    machine_id: uuid.UUID
    machine_code: str
    total_events: int
    events: List[MachineTimelineItem]


class MachineListResponse(BaseModel):
    items: List[MachineResponse]
    total: int


class MachineStatusUpdateRequest(BaseModel):
    operational_status: str


class SensorCycleReading(BaseModel):
    cycle: int
    recorded_at: datetime
    op_setting_1: Optional[float] = None
    op_setting_2: Optional[float] = None
    op_setting_3: Optional[float] = None
    sensors: Dict[str, Optional[float]]
    imputed_fields: Optional[List[str]] = None


class SensorHistoryResponse(BaseModel):
    machine_id: uuid.UUID
    machine_code: str
    total_cycles: int
    returned_cycles: int
    readings: List[SensorCycleReading]
