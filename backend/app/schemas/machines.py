"""
Pydantic schemas for Machine entities and telemetry history
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class MachineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: Optional[uuid.UUID] = None
    machine_code: str
    operational_status: str
    health_indicator: Optional[float] = None
    health_band: Optional[str] = None
    is_demo: bool = False
    demo_cluster: Optional[str] = None
    created_at: datetime
    updated_at: datetime


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
