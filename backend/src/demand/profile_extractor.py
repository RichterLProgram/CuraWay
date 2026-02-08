from __future__ import annotations

from typing import List

from src.demand.capability_mapper import map_demand_to_capabilities
from src.shared.models import DemandRequirements, PatientProfile
from src.shared.utils import compute_urgency_score, extract_all_with_regex, extract_with_regex


def _extract_list_field(pattern: str, text: str) -> List[str]:
    raw = extract_with_regex(pattern, text)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def extract_demand_from_text(text: str) -> DemandRequirements:
    """
    Extract demand requirements from a patient report.

    Uses regex and heuristics to detect diagnosis, stage, biomarkers, location,
    and comorbidities, then maps them to required capabilities.
    """
    patient_id = extract_with_regex(r"patient id:\s*([A-Za-z0-9\-]+)", text) or "unknown"
    diagnosis = extract_with_regex(r"diagnosis:\s*([^\n]+)", text) or "Unknown"
    stage = extract_with_regex(r"stage:\s*([A-Za-z0-9 ]+)", text)
    location = extract_with_regex(r"location:\s*([^\n]+)", text) or "Unknown"
    biomarkers = _extract_list_field(r"biomarkers:\s*([^\n]+)", text)
    comorbidities = _extract_list_field(r"comorbidities:\s*([^\n]+)", text)

    urgency_score = compute_urgency_score(stage, comorbidities)
    required_capabilities = map_demand_to_capabilities(diagnosis, stage, biomarkers)
    travel_radius_km = 30 if urgency_score >= 8 else 60

    evidence = []
    evidence.extend(extract_all_with_regex(r"diagnosis:\s*([^\n]+)", text))
    evidence.extend(extract_all_with_regex(r"stage:\s*([^\n]+)", text))
    evidence.extend(extract_all_with_regex(r"biomarkers:\s*([^\n]+)", text))

    profile = PatientProfile(
        patient_id=patient_id,
        diagnosis=diagnosis,
        stage=stage,
        biomarkers=biomarkers,
        location=location,
        urgency_score=urgency_score,
    )

    return DemandRequirements(
        profile=profile,
        required_capabilities=required_capabilities,
        travel_radius_km=travel_radius_km,
        evidence=evidence,
    )
