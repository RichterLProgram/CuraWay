"""Patient profile for clinical trial matching."""

from typing import List, Optional

from pydantic import BaseModel, Field


class PatientLocation(BaseModel):
    """Optional location for distance calculations."""

    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    label: Optional[str] = None


class PatientProfile(BaseModel):
    """Structured patient profile from a report."""

    cancer_type: Optional[str] = None
    stage: Optional[str] = None
    biomarkers: List[str] = Field(default_factory=list)
    prior_therapy_lines: Optional[int] = None
    ecog_status: Optional[int] = None
    brain_metastases: Optional[bool] = None
    location: Optional[PatientLocation] = None


class PatientEvidenceItem(BaseModel):
    field: str
    snippet: str
    confidence: float
    document_id: str
    chunk_id: str


class PatientExtractionResult(BaseModel):
    profile: PatientProfile
    evidence: list[PatientEvidenceItem] = Field(default_factory=list)
    method: str = "rules"
