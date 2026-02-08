from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.ai.llm_client import call_llm
from src.intelligence.cost_model import estimate_costs
from src.intelligence.hotspot_ranker import rank_hotspots
from src.intelligence.simulation_engine import generate_presets


class PlannerSummaryDraft(BaseModel):
    summary: str


class PlannerEngineRequest(BaseModel):
    region: Optional[str] = None
    demand: Dict[str, Any] = Field(default_factory=dict)
    supply: Dict[str, Any] = Field(default_factory=dict)
    gap: Dict[str, Any] = Field(default_factory=dict)
    hotspots: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    baseline_kpis: Dict[str, Any] = Field(default_factory=dict)


def build_planner_response(payload: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
    request = PlannerEngineRequest.model_validate(payload)
    hotspots = rank_hotspots(request.hotspots or [])
    baseline = request.baseline_kpis or _derive_baseline(request)
    primary_region = request.region or (hotspots[0]["region"] if hotspots else "Region")

    action_plan = _build_action_plan(
        primary_region,
        hotspots[0] if hotspots else None,
        request.recommendations,
        baseline,
    )
    summary = _build_summary(
        primary_region,
        baseline,
        hotspots,
        action_plan,
        trace_id=trace_id,
    )

    return {
        "summary": summary,
        "hotspots": hotspots,
        "action_plan": action_plan,
        "simulation_presets": generate_presets(baseline, hotspots),
    }


def _derive_baseline(request: PlannerEngineRequest) -> Dict[str, Any]:
    demand_total = int(request.demand.get("total_count", 0))
    avg_coverage = float(request.supply.get("avg_coverage", 0))
    underserved = int(request.gap.get("total_population_underserved", 0))
    avg_gap = float(request.gap.get("avg_gap_score", 0))
    return {
        "demand_total": demand_total,
        "avg_coverage": avg_coverage,
        "total_population_underserved": underserved,
        "avg_gap_score": avg_gap,
    }


def _build_action_plan(
    region: str,
    hotspot: Optional[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    baseline: Dict[str, Any],
) -> Dict[str, Any]:
    gap_score = float((hotspot or {}).get("gap_score", baseline.get("avg_gap_score", 0)))
    population = int((hotspot or {}).get("population_affected", baseline.get("total_population_underserved", 0)))
    priority = _priority_from_gap(gap_score)
    confidence = _confidence_from_baseline(baseline)

    cost = estimate_costs(gap_score, population)
    action_list = _actions_from_recommendations(recommendations)

    impact = (
        f"Projected coverage uplift of {int(round(10 + gap_score * 40))}% "
        f"and reduction of ~{max(5, int(population / 1000))}K underserved residents "
        "within 6 months."
    )

    return {
        "region": region,
        "priority": priority,
        "confidence": confidence,
        "estimated_cost": cost.estimated_cost,
        "capex_cost": cost.capex_cost,
        "opex_cost": cost.opex_cost,
        "impact": impact,
        "actions": action_list,
        "timeline": [
            "0-2 weeks: validate demand signals and confirm scope",
            "2-6 weeks: align stakeholders and budget approvals",
            "6-12 weeks: deploy resources and monitor impact",
        ],
        "dependencies": [
            "Requires staffing approval",
            "Supply chain lead time 6–8 weeks",
            "Regional stakeholder alignment",
        ],
        "risks": [
            "Staffing shortfalls in priority specialties",
            "Procurement lead times exceed plan",
        ],
    }


def _actions_from_recommendations(recommendations: List[Dict[str, Any]]) -> List[str]:
    actions = []
    for rec in recommendations[:3]:
        action = rec.get("action") or rec.get("title") or "Targeted capacity upgrades"
        capability = rec.get("capability_needed")
        if capability and capability not in action:
            actions.append(f"{action} for {capability}")
        else:
            actions.append(action)
    if not actions:
        actions = [
            "Expand core oncology capability coverage",
            "Improve referral pathways and transport",
            "Increase diagnostics capacity",
        ]
    return actions


def _priority_from_gap(gap_score: float) -> str:
    if gap_score >= 0.75:
        return "critical"
    if gap_score >= 0.6:
        return "high"
    if gap_score >= 0.4:
        return "medium"
    return "low"


def _confidence_from_baseline(baseline: Dict[str, Any]) -> str:
    demand_total = int(baseline.get("demand_total", 0))
    supply_coverage = float(baseline.get("avg_coverage", 0))
    if demand_total >= 20 and supply_coverage > 40:
        return "high"
    if demand_total >= 10:
        return "medium"
    return "low"


def _build_summary(
    region: str,
    baseline: Dict[str, Any],
    hotspots: List[Dict[str, Any]],
    action_plan: Dict[str, Any],
    trace_id: str,
) -> str:
    prompt = (
        "Provide a 2-3 sentence executive summary for a healthcare planning dashboard. "
        "Use the provided data and keep formatting consistent."
        f"\n\nRegion: {region}"
        f"\nBaseline KPIs: {baseline}"
        f"\nTop hotspot: {hotspots[0] if hotspots else {}}"
        f"\nAction plan: {action_plan}"
    )
    result = call_llm(
        prompt=prompt,
        schema=PlannerSummaryDraft,
        system_prompt="Return ONLY JSON for the schema.",
        trace_id=trace_id,
        step_id="planner_engine_summary",
        input_refs={
            "hotspot_count": len(hotspots),
            "avg_gap_score": baseline.get("avg_gap_score"),
        },
        mock_key="planner_engine_summary",
    )
    return result.parsed.summary
