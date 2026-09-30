"""
Common Pydantic schemas and standard error envelopes
"""

from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthStatus(BaseModel):
    status: str
    environment: str
    database: str
    version: str
