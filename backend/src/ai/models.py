from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from src.shared.models import FacilityLocation


class FacilityCapabilitiesDraft(BaseModel):
    name: Optional[str] = Field(default=None)
    location: Optional[FacilityLocation] = Field(default=None)
    capabilities: List[str] = Field(default_factory=list)
    equipment: List[str] = Field(default_factory=list)
    specialists: List[str] = Field(default_factory=list)
    coverage_score: Optional[float] = Field(default=None, ge=0, le=100)
