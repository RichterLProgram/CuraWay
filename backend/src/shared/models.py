from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class PatientProfile(BaseModel):
    patient_id: str
    diagnosis: str
    stage: Optional[str] = None
    biomarkers: List[str] = Field(default_factory=list)
    location: str
    urgency_score: int = Field(
        ge=0,
        le=10,
        description="0-10 severity scale derived from stage and comorbidities.",
    )


class DemandRequirements(BaseModel):
    profile: PatientProfile
    required_capabilities: List[str] = Field(default_factory=list)
    travel_radius_km: int = Field(default=50, ge=0)
    evidence: List[str] = Field(default_factory=list)


class FacilityLocation(BaseModel):
    lat: float
    lng: float
    region: str


class SupplyEntry(BaseModel):
    name: str
    capability_code: Optional[str] = None
    citation_ids: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    negated: Optional[bool] = None
    evidence: Optional[Dict[str, Any]] = None


class FacilityCapabilities(BaseModel):
    facility_id: str
    name: str
    location: FacilityLocation
    capabilities: List[Union[str, "SupplyEntry"]] = Field(default_factory=list)
    equipment: List[Union[str, "SupplyEntry"]] = Field(default_factory=list)
    specialists: List[Union[str, "SupplyEntry"]] = Field(default_factory=list)
    coverage_score: float = Field(ge=0, le=100)
    citations: List["Citation"] = Field(default_factory=list)
    canonical_capabilities: Optional[List[str]] = None
    capabilities_legacy: Optional[List[str]] = None
    equipment_legacy: Optional[List[str]] = None
    specialists_legacy: Optional[List[str]] = None


class CitationLocator(BaseModel):
    row: Optional[int] = None
    col: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None


class CitationSpan(BaseModel):
    start_char: Optional[int] = None
    end_char: Optional[int] = None


class Citation(BaseModel):
    citation_id: str
    source_doc_id: str
    source_type: Literal["text", "pdf", "table", "web"]
    locator: CitationLocator = Field(default_factory=CitationLocator)
    span: CitationSpan = Field(default_factory=CitationSpan)
    quote: str
    confidence: float = Field(ge=0, le=1)


class Evidence(BaseModel):
    citation_id: Optional[str] = None
    source_doc_id: Optional[str] = None
    row_id: Optional[int] = None
    column_name: Optional[str] = None
    snippet: str = ""


class DesertScoreComponents(BaseModel):
    distance_component: float = Field(ge=0, le=50)
    missing_prerequisites_component: float = Field(ge=0, le=30)
    data_incompleteness_component: float = Field(ge=0, le=20)
    total_score: float = Field(ge=0, le=100)


class DesertScore(BaseModel):
    facility_id: Optional[str] = None
    region_id: Optional[str] = None
    capability_target: str
    distance_km_to_nearest_capable: Optional[float] = None
    missing_prerequisites: List[str] = Field(default_factory=list)
    coverage_gap_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    subscores: DesertScoreComponents
    evidence: List[Evidence] = Field(default_factory=list)
    explanation: str
    step_trace_id: str


class MedicalDesert(BaseModel):
    region_name: str
    lat: float
    lng: float
    demand_count: int
    supply_count: int
    gap_score: float = Field(ge=0, le=1)
    missing_capabilities: List[str] = Field(default_factory=list)


class PlannerRecommendation(BaseModel):
    region_name: str
    priority: str
    missing_capabilities: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    estimated_cost_usd: int
    expected_impact: str


class ImpactEstimate(BaseModel):
    region_name: str
    roi_score: float = Field(ge=0, le=1)
    time_to_treatment_days: int = Field(ge=0)


class MapPoint(BaseModel):
    lat: float
    lng: float
    intensity: float = Field(ge=0, le=1)
    label: str
