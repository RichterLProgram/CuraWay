from __future__ import annotations

import hashlib
import re
from typing import List

from src.shared.models import FacilityCapabilities, FacilityLocation
from src.shared.utils import extract_with_regex, infer_location, normalize_text
from src.supply.coverage_analyzer import calculate_coverage_score


def _infer_capabilities(text: str) -> List[str]:
    capabilities: List[str] = []
    rules = {
        "emergency": "Emergency_care",
        "surgery": "Surgical_services",
        "dialysis": "Dialysis",
        "radiology": "Diagnostic_imaging",
        "imaging": "Diagnostic_imaging",
        "laboratory": "Laboratory_services",
        "pharmacy": "Pharmacy",
        "maternity": "Maternal_care",
        "oncology": "Oncology",
        "ophthalmology": "Ophthalmology",
    }
    for keyword, capability in rules.items():
        if keyword in text:
            capabilities.append(capability)
    return sorted(set(capabilities))


def _extract_labeled_block(label: str, text: str, labels: List[str]) -> str:
    labels_pattern = "|".join(re.escape(item) for item in labels)
    pattern = rf"{label}:\s*(.*?)(?=\n\s*(?:{labels_pattern}):|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).strip().split())


def _extract_list_field(label: str, text: str, labels: List[str]) -> List[str]:
    value = _extract_labeled_block(label, text, labels)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_facility_document(text: str) -> FacilityCapabilities:
    """
    Parse unstructured facility text into structured capabilities.

    Uses regex + keyword inference for capabilities, equipment, and specialists.
    """
    labels = ["Name", "Location", "Services", "Equipment", "Specialists", "Capabilities"]
    name = _extract_labeled_block("Name", text, labels) or "Unknown Facility"
    location_text = _extract_labeled_block("Location", text, labels) or "Unknown"
    lat, lng, region = infer_location(location_text)

    capabilities = _extract_list_field("Capabilities", text, labels)
    equipment = _extract_list_field("Equipment", text, labels)
    specialists = _extract_list_field("Specialists", text, labels)

    inferred = _infer_capabilities(normalize_text(text).lower())
    capabilities = sorted(set(capabilities + inferred))

    coverage_score = calculate_coverage_score(capabilities, equipment, specialists)
    facility_id = hashlib.md5(name.encode("utf-8")).hexdigest()[:10]

    return FacilityCapabilities(
        facility_id=facility_id,
        name=name,
        location=FacilityLocation(lat=lat, lng=lng, region=region),
        capabilities=capabilities,
        equipment=equipment,
        specialists=specialists,
        coverage_score=coverage_score,
    )
