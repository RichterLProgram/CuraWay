from __future__ import annotations

from src.ai.llm_extractors import extract_demand_requirements
from src.shared.models import DemandRequirements


def extract_demand_from_text(
    text: str,
    trace_id: str | None = None,
) -> DemandRequirements:
    """
    Extract demand requirements from a patient report using the LLM gateway.
    """
    return extract_demand_requirements(text, trace_id=trace_id)
