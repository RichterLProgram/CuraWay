from __future__ import annotations

import re
from typing import List

from src.shared.models import DemandRequirements, PatientProfile
from src.shared.utils import infer_location
from src.intelligence.gap_detection import _load_capability_mappings


def parse_demand_fallback(text: str) -> DemandRequirements:
    diagnosis = _extract_diagnosis(text) or "Unknown"
    stage = _extract_stage(text)
    biomarkers = _extract_biomarkers(text)
    location_text = _extract_location(text) or "Unknown"
    _, _, region = infer_location(location_text)
    required = _derive_required_from_mapping(diagnosis)

    profile = PatientProfile(
        patient_id="fallback-patient",
        diagnosis=diagnosis,
        stage=stage,
        biomarkers=biomarkers,
        location=location_text,
        urgency_score=5,
    )
    return DemandRequirements(
        profile=profile,
        required_capabilities=required,
        travel_radius_km=50,
        evidence=[diagnosis],
    )


def _extract_diagnosis(text: str) -> str | None:
    match = re.search(r"diagnosis:\s*(.+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_stage(text: str) -> str | None:
    match = re.search(r"stage:\s*(i{1,3}|iv|v)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _extract_biomarkers(text: str) -> List[str]:
    match = re.search(r"biomarkers:\s*(.+)", text, flags=re.IGNORECASE)
    if match:
        return [item.strip() for item in match.group(1).split(",") if item.strip()]
    return []


def _extract_location(text: str) -> str | None:
    match = re.search(r"location:\s*(.+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _derive_required_from_mapping(diagnosis: str) -> List[str]:
    mappings = _load_capability_mappings()
    diagnosis_lower = diagnosis.lower()
    required: List[str] = []
    for entry in mappings:
        match = entry.get("match", "").lower()
        if match and match in diagnosis_lower:
            required.extend(entry.get("capabilities", []))
    return sorted(set(required)) or ["ONC_GENERAL"]
