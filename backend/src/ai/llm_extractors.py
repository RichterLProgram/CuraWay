from __future__ import annotations

import hashlib
from typing import Any, Mapping, Optional

from src.ai.llm_client import call_llm
from src.ai.models import FacilityCapabilitiesDraft
from src.ai.prompts import (
    DEMAND_REQUIREMENTS_SYSTEM_PROMPT,
    FACILITY_CAPABILITIES_SYSTEM_PROMPT,
)
from src.ontology.normalize import normalize_supply
from src.shared.models import DemandRequirements, FacilityCapabilities, FacilityLocation
from src.supply.citations import attach_row_citations


def _format_mapping_as_text(row: Mapping[str, str]) -> str:
    lines = ["CSV Row:"]
    for key, value in row.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        lines.append(f"{key}: {text}")
    return "\n".join(lines)


def extract_facility_capabilities(
    text: str,
    trace_id: Optional[str] = None,
    input_refs: Optional[Mapping[str, Any]] = None,
) -> FacilityCapabilities:
    result = call_llm(
        prompt=text,
        schema=FacilityCapabilitiesDraft,
        system_prompt=FACILITY_CAPABILITIES_SYSTEM_PROMPT,
        trace_id=trace_id,
        step_id="facility_extract",
        input_refs=dict(input_refs or {}),
        mock_key="facility_capabilities",
    )
    draft = result.parsed
    name = draft.name or "Unknown Facility"
    location = draft.location or FacilityLocation(lat=0.0, lng=0.0, region="Unknown")
    capabilities = draft.capabilities or []
    equipment = draft.equipment or []
    specialists = draft.specialists or []
    coverage_score = float(draft.coverage_score or 0.0)
    facility_id = hashlib.md5(name.encode("utf-8")).hexdigest()[:10]

    return FacilityCapabilities(
        facility_id=facility_id,
        name=name,
        location=location,
        capabilities=capabilities,
        equipment=equipment,
        specialists=specialists,
        coverage_score=coverage_score,
    )


def extract_demand_requirements(
    text: str,
    trace_id: Optional[str] = None,
) -> DemandRequirements:
    result = call_llm(
        prompt=text,
        schema=DemandRequirements,
        system_prompt=DEMAND_REQUIREMENTS_SYSTEM_PROMPT,
        trace_id=trace_id,
        step_id="demand_extract",
        input_refs={"text_length": len(text)},
        mock_key="demand_requirements",
    )
    return result.parsed


def extract_facility_from_csv_row(
    row: Mapping[str, str],
    row_index: int | None = None,
    source_doc_id: str | None = None,
    trace_id: Optional[str] = None,
) -> FacilityCapabilities:
    text = _format_mapping_as_text(row)
    input_refs = {
        "row_index": row_index,
        "source_doc_id": source_doc_id or "facility_table",
        "columns": list(row.keys()),
    }
    result = extract_facility_capabilities(text, trace_id=trace_id, input_refs=input_refs)
    if row_index is None:
        return normalize_supply(result, source_text=text)
    doc_id = source_doc_id or "facility_table"
    result = attach_row_citations(
        result,
        row_index,
        doc_id,
        row_values=row,
        chunk_id=f"row_{row_index}",
    )
    return normalize_supply(result, source_text=text)
