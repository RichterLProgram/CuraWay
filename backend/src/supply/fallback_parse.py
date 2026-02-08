from __future__ import annotations

import re
from typing import List

from src.ontology.normalize import load_ontology, normalize_supply
from src.shared.models import FacilityCapabilities, FacilityLocation
from src.supply.citations import attach_text_citations


def parse_supply_fallback(text: str, source_doc_id: str) -> FacilityCapabilities:
    ontology = load_ontology()
    capabilities: List[str] = []
    lower = text.lower()
    for code, info in (ontology.get("capabilities") or {}).items():
        synonyms = [info.get("display_name", code)] + list(info.get("synonyms", []))
        if any(str(syn).lower() in lower for syn in synonyms if syn):
            capabilities.append(info.get("display_name", code))

    facility = FacilityCapabilities(
        facility_id="fallback-facility",
        name=_extract_name(text) or "Fallback Facility",
        location=FacilityLocation(lat=0.0, lng=0.0, region="Unknown"),
        capabilities=capabilities,
        equipment=[],
        specialists=[],
        coverage_score=0.0,
    )
    facility = attach_text_citations(
        facility, text, source_doc_id, source_type="text", chunk_id="chunk_0"
    )
    return normalize_supply(facility, source_text=text)


def _extract_name(text: str) -> str | None:
    match = re.search(r"Name:\s*(.+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
