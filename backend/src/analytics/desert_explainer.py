from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from src.ai.llm_client import call_llm
from src.shared.models import Evidence


class DesertExplainResult(BaseModel):
    normalized_target: str
    confidence: float = Field(ge=0, le=1)
    explanation: str
    risk_flags: List[str] = Field(default_factory=list)


def explain_desert(
    capability_target: str,
    suggested_target: str,
    missing_prerequisites: List[str],
    distance_km_to_nearest_capable: Optional[float],
    evidence: List[Evidence],
    trace_id: str,
    step_id: str,
) -> DesertExplainResult:
    evidence_payload = [
        {
            "row_id": item.row_id,
            "snippet": item.snippet,
            "source_doc_id": item.source_doc_id,
        }
        for item in evidence
    ]
    prompt = (
        "You are validating a medical desert score. "
        "Normalize the capability target to a canonical ontology code if needed. "
        "Check whether the prerequisites list seems plausible. "
        "Write a concise explanation that ONLY uses the provided evidence snippets. "
        "Cite evidence rows inline using [row <id>] and do not add new facts."
        "\n\nInput capability target:\n"
        f"{capability_target}\n"
        f"Suggested canonical target: {suggested_target}\n"
        f"Missing prerequisites: {missing_prerequisites}\n"
        f"Distance to nearest capable (km): {distance_km_to_nearest_capable}\n"
        f"Evidence snippets: {evidence_payload}\n"
    )
    result = call_llm(
        prompt=prompt,
        schema=DesertExplainResult,
        system_prompt="Return ONLY JSON for the schema. Explanations must cite [row <id>].",
        trace_id=trace_id,
        step_id=step_id,
        input_refs={
            "missing_prereq_count": len(missing_prerequisites),
            "evidence_count": len(evidence),
        },
        mock_key="desert_score_explain",
    )
    return result.parsed
