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
