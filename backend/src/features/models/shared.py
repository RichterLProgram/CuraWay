"""Shared Pydantic models used across modules for auditability and reuse."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal


class EvidenceSnippet(BaseModel):
    """Auditable evidence snippet with document and chunk provenance."""

    text: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)


class CapabilityDecision(BaseModel):
    """Jury-facing decision record for a single capability."""

    value: bool
    confidence: float
    decision_reason: Literal[
        "direct_evidence",
        "insufficient_evidence",
        "conflicting_evidence",
        "suspicious_claim",
    ]
    evidence: List[EvidenceSnippet]


class RegionalRiskLevel(BaseModel):
    """Risk level descriptor for regional medical access."""

    level: Literal["low", "medium", "high"]


class FacilityWithCapabilityDecisions(BaseModel):
    """Facility record used by regional aggregation modules."""

    facility_id: str = Field(..., min_length=1)
    region: Optional[str] = None
    capability_decisions: Dict[str, dict]


class RegionalAssessment(BaseModel):
    """Regional assessment output for medical desert analysis."""

    region: str
    coverage_score: float
    risk_level: RegionalRiskLevel
    explanation: str
    facility_ids: List[str]
    missing_capabilities: List[str] = Field(default_factory=list)
