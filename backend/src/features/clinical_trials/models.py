"""Modelle für Clinical Trials und Matching-Ergebnisse."""

from typing import List, Optional

from pydantic import BaseModel, Field

from features.patient.profile import PatientProfile


class TrialLocation(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TrialRecord(BaseModel):
    nct_id: str
    title: str
    phase: Optional[str] = None
    status: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    interventions: List[str] = Field(default_factory=list)
    eligibility_criteria: Optional[str] = None
    locations: List[TrialLocation] = Field(default_factory=list)


class EligibilitySignal(BaseModel):
    key: str
    passed: Optional[bool]
    detail: str
    evidence_snippet: Optional[str] = None
    evidence_confidence: Optional[float] = None
    evidence_document_id: Optional[str] = None
    evidence_chunk_id: Optional[str] = None


class TrialMatch(BaseModel):
    trial: TrialRecord
    match_score: float
    eligibility_signals: List[EligibilitySignal]
    distance_km: Optional[float] = None
    travel_time_minutes: Optional[float] = None
    explanation: Optional[str] = None


class TrialSummary(BaseModel):
    nct_id: str
    title: str
    match_score: float
    phase: Optional[str] = None
    status: Optional[str] = None
    distance_km: Optional[float] = None
    travel_time_minutes: Optional[float] = None
    explanation: Optional[str] = None


class BackendReferenceData(BaseModel):
    virtue_foundation_records: int
    scheme_doc_title: str
    prompt_model_files: List[str]


class TrialMatchingResult(BaseModel):
    patient_profile: PatientProfile
    patient_evidence: list = Field(default_factory=list)
    extraction_method: Optional[str] = None
    query: str
    matches: List[TrialMatch]
    top_matches: List[TrialSummary]
    reference_data: BackendReferenceData
    agent_trace: dict = Field(default_factory=dict)
