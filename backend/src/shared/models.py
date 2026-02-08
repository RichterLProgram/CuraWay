from __future__ import annotations

from typing import List, Optional

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


class FacilityCapabilities(BaseModel):
    facility_id: str
    name: str
    location: FacilityLocation
    capabilities: List[str] = Field(default_factory=list)
    equipment: List[str] = Field(default_factory=list)
    specialists: List[str] = Field(default_factory=list)
    coverage_score: float = Field(ge=0, le=100)


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
