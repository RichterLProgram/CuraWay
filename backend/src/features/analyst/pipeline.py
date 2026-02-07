"""Build analyst map data from deserts + demand."""

from typing import List

from features.analyst.models import (
    AnalystApiData,
    AnalystMapData,
    AnalystTrace,
    DemandPoint,
    HeatmapRegion,
    PlannerRecommendation,
)
from features.models.shared import RegionalAssessment


def build_analyst_map_data(
    desert_regions: List[RegionalAssessment],
    demand_points: List[DemandPoint],
) -> AnalystMapData:
    trace = AnalystTrace(
        agent_id="agent.analyst_view.v1",
        demand_points=len(demand_points),
        desert_regions=len(desert_regions),
    )
    return AnalystMapData(
        demand_points=demand_points,
        desert_regions=desert_regions,
        trace=trace,
    )


def build_analyst_api_data(
    desert_regions: List[RegionalAssessment],
    demand_points: List[DemandPoint],
    meta: dict | None = None,
) -> AnalystApiData:
    heatmap = [
        HeatmapRegion(
            region=region.region,
            coverage_score=region.coverage_score,
            risk_level=region.risk_level.level,
            explanation=region.explanation,
        )
        for region in desert_regions
    ]
    planner = [
        PlannerRecommendation(
            region=region.region,
            missing_capabilities=region.missing_capabilities,
            summary=_planner_summary(region),
            priority=_planner_priority(region),
            actions=_planner_actions(region),
            impact_notes=_planner_impact(region),
        )
        for region in desert_regions
        if region.missing_capabilities
    ]
    return AnalystApiData(
        pins=demand_points,
        heatmap=heatmap,
        planner=planner,
        meta=meta or {},
    )


def _planner_summary(region: RegionalAssessment) -> str:
    missing = ", ".join(region.missing_capabilities[:4])
    return f"Focus on: {missing}" if missing else "No critical gaps detected."


def _planner_priority(region: RegionalAssessment) -> str:
    level = region.risk_level.level
    if level == "high":
        return "urgent"
    if level == "medium":
        return "high"
    return "moderate"


def _planner_actions(region: RegionalAssessment) -> List[str]:
    actions = []
    for cap in region.missing_capabilities[:4]:
        if cap == "oncology_services":
            actions.append("Designate oncology lead and establish referral pathway.")
        elif cap == "ct_scanner":
            actions.append("Procure or share CT imaging access with nearby facility.")
        elif cap == "mri_scanner":
            actions.append("Assess MRI demand and negotiate shared service contract.")
        elif cap == "pathology_lab":
            actions.append("Set up pathology sample transport and partner lab.")
        elif cap == "chemotherapy_delivery":
            actions.append("Train staff for chemo delivery and safety protocols.")
        elif cap == "icu":
            actions.append("Add ICU beds or upgrade critical care unit.")
        else:
            actions.append(f"Plan upgrade for {cap.replace('_', ' ')}.")
    return actions or ["Validate capabilities and update facility inventory."]


def _planner_impact(region: RegionalAssessment) -> str | None:
    if region.risk_level.level == "high":
        return "High potential to reduce delayed treatment and improve referral speed."
    if region.risk_level.level == "medium":
        return "Moderate impact through targeted upgrades and coordination."
    return "Lower impact; focus on maintaining existing coverage."
