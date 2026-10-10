# ai-service2/app/schemas/health.py

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    name: str
    status: str
    critical: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    service: str
    version: str
    status: str
    ready: bool
    checked_at: datetime
    checks: List[HealthCheck] = Field(default_factory=list)

