from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.ai.llm_client import call_llm
from validation.validator import ValidationResult, validate_supply as validate_supply_rules


class LlmCriticResult(BaseModel):
    verdict: Literal["plausible", "suspicious", "impossible"]
    rationale: str
    evidence_refs: List[str] = Field(default_factory=list)


def validate_supply(
    supply_json: Dict[str, Any],
    facility_schema: Optional[Dict[str, Any]] = None,
    constraints: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> ValidationResult:
    rule_result = validate_supply_rules(
        supply_json, facility_schema, constraints, trace_id=trace_id
    )
    critic = _llm_critic(
        supply_json,
        rule_result,
        facility_schema=facility_schema,
        constraints=constraints,
        trace_id=rule_result.trace_id,
    )
    final_verdict = _max_verdict(rule_result.verdict, critic.verdict)
    explanation = rule_result.explanation
    if critic.rationale:
        explanation = f"{explanation} LLM-Critic: {critic.rationale}"

    return rule_result.model_copy(
        update={
            "verdict": final_verdict,
            "llm_verdict": critic.verdict,
            "llm_rationale": critic.rationale,
            "llm_evidence_refs": critic.evidence_refs,
            "explanation": explanation,
        }
    )


def _llm_critic(
    supply_json: Dict[str, Any],
    rule_result: ValidationResult,
    facility_schema: Optional[Dict[str, Any]],
    constraints: Optional[Dict[str, Any]],
    trace_id: str,
) -> LlmCriticResult:
    prompt = (
        "You are a medical supply validator. "
        "Assess plausibility and internal consistency for the supply JSON. "
        "Rules have already been applied; do not contradict them. "
        "Return a verdict, rationale, and evidence citation ids if present."
        "\n\nSupply:\n"
        f"{supply_json}\n\n"
        f"Rules verdict: {rule_result.verdict}\n"
        f"Rules issues: {[issue.model_dump() for issue in rule_result.issues]}\n"
        f"Facility schema: {facility_schema}\n"
        f"Constraints: {constraints}"
    )
    result = call_llm(
        prompt=prompt,
        schema=LlmCriticResult,
        system_prompt="Return ONLY JSON for the schema.",
        trace_id=trace_id,
        step_id="validator_critic",
        input_refs={
            "supply_keys": list(supply_json.keys()),
            "rule_verdict": rule_result.verdict,
        },
        mock_key="validator_critic",
    )
    return result.parsed


def _max_verdict(
    current: Literal["plausible", "suspicious", "impossible"],
    candidate: Literal["plausible", "suspicious", "impossible"],
) -> Literal["plausible", "suspicious", "impossible"]:
    order = {"plausible": 0, "suspicious": 1, "impossible": 2}
    return candidate if order[candidate] > order[current] else current
