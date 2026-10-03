"""
Pydantic schemas for Maintenance Workflows and Human-in-the-Loop Actions.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class MaintenanceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    alert_id: Optional[uuid.UUID] = None
    issue: Optional[str] = None
    recommended_action: Optional[str] = None
    decision: Optional[str] = None
    decision_rationale: Optional[str] = None
    action_taken: Optional[str] = None
    action_type: str
    status: str
    outcome: Optional[str] = None
    engineer_notes: str
    performed_by_user_id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None


class MaintenanceListResponse(BaseModel):
    items: List[MaintenanceRecordResponse]
    total: int


class CreateMaintenanceRequest(BaseModel):
    machine_id: uuid.UUID
    alert_id: Optional[uuid.UUID] = None
    issue: Optional[str] = None
    recommended_action: Optional[str] = None
    decision: str  # 'followed_recommendation' | 'modified' | 'declined'
    decision_rationale: str
    action_taken: str
    action_type: Optional[str] = "inspection"
    status: Optional[str] = "in_progress"
    outcome: Optional[str] = None  # 'resolved' | 'no_issue_found' | 'unresolved'
    notes: Optional[str] = ""



class CompleteMaintenanceRequest(BaseModel):
    outcome: str  # 'resolved' | 'no_issue_found' | 'unresolved'
    engineer_notes: Optional[str] = ""
