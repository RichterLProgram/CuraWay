from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.ai.llm_client import call_llm
from src.intelligence.gap_detection import detect_gaps


class PlanLocation(BaseModel):
    lat: float
    lon: float
    region: str


class PlanDemand(BaseModel):
    diagnosis: str
    stage: Optional[str] = None
    biomarkers: List[str] = Field(default_factory=list)
    location: PlanLocation
    urgency: int = Field(ge=0, le=10)
    required_capabilities: List[str] = Field(default_factory=list)
    required_capability_codes: List[str] = Field(default_factory=list)


class PlanSupplyFacility(BaseModel):
    facility_id: str
    name: str
    location: PlanLocation
    capabilities: List[Any] = Field(default_factory=list)
    validation: Optional[Dict[str, Any]] = None


class FacilityTarget(BaseModel):
    facility_id: str
    name: str
    distance_km: float


class ImpactEstimate(BaseModel):
    metric: str
    value: float | int
    unit: str


class ActionCard(BaseModel):
    action_id: str
    type: Literal["route_patient", "refer", "invest", "staffing"]
    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    expected_impact: ImpactEstimate
    confidence: float = Field(ge=0, le=1)
    dependencies: List[str] = Field(default_factory=list)
    facility_targets: List[FacilityTarget] = Field(default_factory=list)
    missing_capability_codes: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    trace_id: str


class PlanRequest(BaseModel):
    demand: Dict[str, Any]
    supply: List[Dict[str, Any]]
    gaps: Optional[List[Dict[str, Any]]] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class PlanResponse(BaseModel):
    trace_id: str
    immediate: List[ActionCard] = Field(default_factory=list)
    near_term: List[ActionCard] = Field(default_factory=list)
    invest: List[ActionCard] = Field(default_factory=list)
    rationale: str
    plan_steps: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    map: Optional[Dict[str, Any]] = None


class PlanStepsDraft(BaseModel):
    plan_steps: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    rationale: str = ""


class QueryPlanDraft(BaseModel):
    intent: str
    radius_km: int = Field(default=200, ge=0)
    region: Optional[str] = None
    required_capabilities: List[str] = Field(default_factory=list)
    plan_steps: List[str] = Field(default_factory=list)


DEFAULT_PARAMS = {
    "radius_km": 200,
    "top_k": 5,
    "threshold": 0.6,
    "time_horizon_days": 90,
    "budget_band": "medium",
    "objectives": [],
}


def plan_actions(payload: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
    request = PlanRequest.model_validate(payload)
    params = dict(DEFAULT_PARAMS)
    params.update(request.params or {})

    gap_response = (
        {"gaps": request.gaps, "map": None}
        if request.gaps
        else detect_gaps(request.demand, request.supply, params, trace_id=trace_id)
    )
    gaps = gap_response.get("gaps") or []
    map_payload = gap_response.get("map")

    immediate: List[ActionCard] = []
    near_term: List[ActionCard] = []
    invest: List[ActionCard] = []

    for gap in gaps:
        candidates = gap.get("candidate_facilities", [])
        missing_codes = gap.get("missing_capabilities", [])
        desert_score = float(gap.get("desert_score", 0))
        demand_urgency = _extract_urgency(request.demand)

        has_suspicious = _has_suspicious_supply(request.supply)
        if candidates:
            immediate.append(
                _route_patient_card(
                    candidates,
                    request.supply,
                    missing_codes,
                    demand_urgency,
                    trace_id,
                )
            )
            if missing_codes:
                near_term.append(
                    _refer_card(
                        candidates,
                        missing_codes,
                        demand_urgency,
                        trace_id,
                    )
                )
            if has_suspicious:
                near_term.append(
                    _staffing_card(
                        request.supply,
                        missing_codes,
                        demand_urgency,
                        trace_id,
                    )
                )
        else:
            if desert_score >= 0.7:
                if request.supply:
                    near_term.append(
                        _refer_card(
                            [],
                            missing_codes,
                            demand_urgency,
                            trace_id,
                        )
                    )
                else:
                    invest.append(
                        _invest_card(missing_codes, demand_urgency, trace_id)
                    )
            elif has_suspicious:
                near_term.append(
                    _staffing_card(
                        request.supply,
                        missing_codes,
                        demand_urgency,
                        trace_id,
                    )
                )
            else:
                near_term.append(
                    _refer_card(
                        [],
                        missing_codes,
                        demand_urgency,
                        trace_id,
                    )
                )

    rationale = _build_rationale(gaps)
    plan_steps, next_actions, llm_rationale = _llm_plan_steps(
        request.demand, request.supply, gaps, params, trace_id
    )
    if llm_rationale:
        rationale = llm_rationale

    response = PlanResponse(
        trace_id=trace_id,
        immediate=immediate,
        near_term=near_term,
        invest=invest,
        rationale=rationale,
        plan_steps=plan_steps,
        next_actions=next_actions,
        map=map_payload,
    )
    return response.model_dump()


def plan_from_query(payload: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    demand = payload.get("demand") or {}
    supply = payload.get("supply") or []
    params = payload.get("params") or {}
    interpretation = _interpret_query(query, trace_id)
    params = dict(params)
    params["radius_km"] = interpretation.radius_km or params.get("radius_km")
    plan_payload = {"demand": demand, "supply": supply, "params": params}
    results = plan_actions(plan_payload, trace_id=trace_id)
    citations = _collect_plan_citations(results)
    return {
        "trace_id": trace_id,
        "query": query,
        "plan": {
            "intent": interpretation.intent,
            "region": interpretation.region,
            "required_capabilities": interpretation.required_capabilities,
            "steps": interpretation.plan_steps or results.get("plan_steps", []),
        },
        "results": results,
        "citations": citations,
        "next_actions": results.get("next_actions", []),
    }


def _route_patient_card(
    candidates: List[Dict[str, Any]],
    supply: List[Dict[str, Any]],
    missing_codes: List[str],
    urgency: int,
    trace_id: str,
) -> ActionCard:
    top = candidates[:2]
    targets = _facility_targets(top, supply)
    citations = _collect_citations(top, supply)
    priority = "high" if urgency >= 8 else "medium"
    confidence = _confidence_from_citations(citations, base=0.75)
    return ActionCard(
        action_id=str(uuid.uuid4()),
        type="route_patient",
        title="Route patient to top facility",
        description="Direct patient to the highest coverage facility within radius.",
        priority=priority,
        expected_impact=ImpactEstimate(metric="patients/week", value=1, unit="patients"),
        confidence=confidence,
        dependencies=["transport_availability"],
        facility_targets=targets,
        missing_capability_codes=missing_codes,
        citations=citations,
        trace_id=trace_id,
    )


def _refer_card(
    candidates: List[Dict[str, Any]],
    missing_codes: List[str],
    urgency: int,
    trace_id: str,
) -> ActionCard:
    priority = "high" if urgency >= 8 else "medium"
    targets = []
    if candidates:
        targets = [
            FacilityTarget(
                facility_id=candidates[0]["facility_id"],
                name="Referral facility",
                distance_km=candidates[0]["distance_km"],
            )
        ]
    return ActionCard(
        action_id=str(uuid.uuid4()),
        type="refer",
        title="Refer for missing capabilities",
        description="Refer to a facility that can cover missing capabilities.",
        priority=priority,
        expected_impact=ImpactEstimate(metric="patients/week", value=1, unit="patients"),
        confidence=0.6,
        dependencies=["referral_protocol"],
        facility_targets=targets,
        missing_capability_codes=missing_codes,
        citations=[],
        trace_id=trace_id,
    )


def _staffing_card(
    supply: List[Dict[str, Any]],
    missing_codes: List[str],
    urgency: int,
    trace_id: str,
) -> ActionCard:
    priority = "high" if urgency >= 8 else "medium"
    citations = _collect_citations([], supply, prefer_suspicious=True)
    confidence = _confidence_from_citations(citations, base=0.55)
    return ActionCard(
        action_id=str(uuid.uuid4()),
        type="staffing",
        title="Staffing uplift for missing capabilities",
        description="Assign staff or training to cover missing capability gaps.",
        priority=priority,
        expected_impact=ImpactEstimate(metric="patients/week", value=1, unit="patients"),
        confidence=confidence,
        dependencies=["staffing_plan"],
        facility_targets=[],
        missing_capability_codes=missing_codes,
        citations=citations,
        trace_id=trace_id,
    )


def _invest_card(
    missing_codes: List[str],
    urgency: int,
    trace_id: str,
) -> ActionCard:
    priority = "high" if urgency >= 8 else "medium"
    return ActionCard(
        action_id=str(uuid.uuid4()),
        type="invest",
        title="Invest in local capability expansion",
        description="Invest in equipment or services to close high-severity gaps.",
        priority=priority,
        expected_impact=ImpactEstimate(metric="patients/week", value=2, unit="patients"),
        confidence=0.65,
        dependencies=["budget_approval"],
        facility_targets=[],
        missing_capability_codes=missing_codes,
        citations=[],
        trace_id=trace_id,
    )


def _facility_targets(
    candidates: List[Dict[str, Any]],
    supply: List[Dict[str, Any]],
) -> List[FacilityTarget]:
    targets: List[FacilityTarget] = []
    name_lookup = {item.get("facility_id"): item.get("name") for item in supply}
    for candidate in candidates:
        facility_id = candidate.get("facility_id")
        name = name_lookup.get(facility_id, "Facility")
        targets.append(
            FacilityTarget(
                facility_id=facility_id,
                name=name,
                distance_km=float(candidate.get("distance_km", 0)),
            )
        )
    return targets


def _collect_citations(
    candidates: List[Dict[str, Any]],
    supply: List[Dict[str, Any]],
    prefer_suspicious: bool = False,
) -> List[str]:
    citations: List[str] = []
    facility_ids = [item.get("facility_id") for item in candidates if item.get("facility_id")]
    for facility in supply:
        if prefer_suspicious and (facility.get("validation", {}) or {}).get("verdict") != "suspicious":
            continue
        if facility_ids and facility.get("facility_id") not in facility_ids:
            continue
        for entry in facility.get("capabilities", []):
            if isinstance(entry, dict):
                citations.extend(entry.get("citation_ids") or [])
    return list(dict.fromkeys([cid for cid in citations if cid]))


def _confidence_from_citations(citations: List[str], base: float) -> float:
    if citations:
        return min(1.0, base + 0.1)
    return base


def _extract_urgency(demand: Dict[str, Any]) -> int:
    return int(
        demand.get("urgency")
        or (demand.get("profile", {}) or {}).get("urgency_score")
        or 5
    )


def _build_rationale(gaps: List[Dict[str, Any]]) -> str:
    if not gaps:
        return "No gaps detected."
    worst = max(gaps, key=lambda item: item.get("desert_score", 0))
    score = worst.get("desert_score", 0)
    if score >= 0.7:
        return "High desert score indicates urgent investment needs."
    if score >= 0.4:
        return "Moderate gaps exist; targeted staffing recommended."
    return "Coverage is generally adequate within radius."


def _llm_plan_steps(
    demand: Dict[str, Any],
    supply: List[Dict[str, Any]],
    gaps: List[Dict[str, Any]],
    params: Dict[str, Any],
    trace_id: str,
) -> tuple[List[str], List[str], str]:
    prompt = (
        "You are an NGO planning assistant. "
        "Given demand, supply and gap analysis, return 3-6 concise plan steps and "
        "2-4 next action suggestions. Be pragmatic and avoid speculation."
        "\n\nDemand:\n"
        f"{demand}\n\nSupply count: {len(supply)}\n\n"
        f"Gaps: {gaps}\n\nParams: {params}"
    )
    result = call_llm(
        prompt=prompt,
        schema=PlanStepsDraft,
        system_prompt="Return a concise action plan for NGO operations.",
        trace_id=trace_id,
        step_id="plan_steps",
        input_refs={"supply_count": len(supply), "gap_count": len(gaps)},
        mock_key="plan_steps",
    )
    draft = result.parsed
    return draft.plan_steps or [], draft.next_actions or [], draft.rationale or ""


def _interpret_query(query: str, trace_id: str) -> QueryPlanDraft:
    prompt = (
        "Interpret the user query for an NGO planning task. "
        "Extract intent, radius_km if mentioned, region, and required capabilities."
        f"\n\nQuery: {query}"
    )
    result = call_llm(
        prompt=prompt,
        schema=QueryPlanDraft,
        system_prompt="Return ONLY JSON for the schema.",
        trace_id=trace_id,
        step_id="query_interpretation",
        input_refs={"query_length": len(query)},
        mock_key="query_interpretation",
    )
    return result.parsed


def _collect_plan_citations(results: Dict[str, Any]) -> List[str]:
    citations: List[str] = []
    for bucket in ["immediate", "near_term", "invest"]:
        for card in results.get(bucket, []) or []:
            citations.extend(card.get("citations") or [])
    return list(dict.fromkeys([cid for cid in citations if cid]))


def _has_suspicious_supply(supply: List[Dict[str, Any]]) -> bool:
    for facility in supply:
        verdict = (facility.get("validation", {}) or {}).get("verdict")
        if verdict == "suspicious":
            return True
    return False
