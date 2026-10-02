"""
Pydantic schemas for Scoring Runs.
PRD §14.4
"""

import uuid
from typing import List, Optional

from pydantic import BaseModel


class ScoringRunRequest(BaseModel):
    dataset_id: uuid.UUID
    machine_ids: Optional[List[uuid.UUID]] = None


class ScoringRunResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str
