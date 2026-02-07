"""FacilityInfo, Capabilities, Evidence – IDP output schemas."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class FacilityInfo(BaseModel):
    """Core facility identifiers extracted from text."""

    facility_name: str = Field(..., min_length=1)
    country: Optional[str] = None
    region: Optional[str] = None


class Capabilities(BaseModel):
    """Binary capability flags for a medical facility."""

    oncology_services: bool
    ct_scanner: bool
    mri_scanner: bool
    pathology_lab: bool
    genomic_testing: bool
    chemotherapy_delivery: bool
    radiotherapy: bool
    icu: bool
    trial_coordinator: bool


class Metadata(BaseModel):
    """Evidence and confidence metadata for each capability."""

    confidence_scores: Dict[str, float]
    extracted_evidence: Dict[str, List[object]]
    suspicious_claims: List[str]

    @field_validator("confidence_scores")
    @classmethod
    def validate_confidences(cls, value: Dict[str, float]) -> Dict[str, float]:
        for key, score in value.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"Confidence score for {key} out of range: {score}")
        return value


class CapabilitySchema(BaseModel):
    """Validated output schema for the IDP agent."""

    facility_info: FacilityInfo
    capabilities: Capabilities
    metadata: Metadata

    @model_validator(mode="before")
    @classmethod
    def validate_alignment(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        capabilities = values.get("capabilities")
        metadata = values.get("metadata")
        if not capabilities or not metadata:
            return values
        cap_keys = (
            capabilities.model_dump().keys()
            if hasattr(capabilities, "model_dump")
            else capabilities.keys()
        )
        capability_keys = set(cap_keys)
        meta_conf = (
            metadata.confidence_scores
            if hasattr(metadata, "confidence_scores")
            else metadata.get("confidence_scores", {})
        )
        meta_ev = (
            metadata.extracted_evidence
            if hasattr(metadata, "extracted_evidence")
            else metadata.get("extracted_evidence", {})
        )
        confidence_keys = set(meta_conf.keys())
        evidence_keys = set(meta_ev.keys())
        if capability_keys != confidence_keys:
            raise ValueError("confidence_scores keys must match capability keys")
        if capability_keys != evidence_keys:
            raise ValueError("extracted_evidence keys must match capability keys")
        return values


class EvidenceSnippet(BaseModel):
    """Auditable evidence snippet with document and chunk provenance."""

    text: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    chunk_id: str = Field(..., min_length=1)
