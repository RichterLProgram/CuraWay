"""Build analyst map data from deserts + demand."""

from typing import List

from analyst.models import (
    AnalystApiData,
    AnalystMapData,
    AnalystTrace,
    DemandPoint,
    HeatmapRegion,
    PlannerRecommendation,
)
from models.shared import RegionalAssessment


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
