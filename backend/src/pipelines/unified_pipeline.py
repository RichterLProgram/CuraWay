from __future__ import annotations

from typing import List

from src.intelligence.gap_detector import detect_deserts
from src.intelligence.impact_estimator import estimate_impact
from src.intelligence.planner import generate_recommendations
from src.intelligence.planner_engine import build_planner_response
from src.pipelines.demand_pipeline import run_demand_pipeline
from src.pipelines.supply_pipeline import run_supply_pipeline
from src.shared.models import MapPoint
from src.shared.utils import infer_location, write_json


def _build_map_points(demand_results, supply_results, deserts) -> List[MapPoint]:
    points: List[MapPoint] = []

    for demand in demand_results:
        lat, lng, _ = infer_location(demand.profile.location)
        points.append(
            MapPoint(
                lat=lat,
                lng=lng,
                intensity=min(demand.profile.urgency_score / 10, 1.0),
                label=f"Demand:{demand.profile.patient_id}",
            )
        )

    for facility in supply_results:
        points.append(
            MapPoint(
                lat=facility.location.lat,
                lng=facility.location.lng,
                intensity=min(facility.coverage_score / 100, 1.0),
                label=f"Supply:{facility.name}",
            )
        )

    for desert in deserts:
        points.append(
            MapPoint(
                lat=desert.lat,
                lng=desert.lng,
                intensity=desert.gap_score,
                label=f"Desert:{desert.region_name}",
            )
        )

    return points


def run_full_analysis():
    """
    1. Load patient reports → extract demand
    2. Load facility docs → extract supply
    3. Detect gaps
    4. Generate planner recommendations
    5. Write JSONs to output/data/

    Output files:
      - demand_data.json
      - supply_data.json
      - gap_analysis.json
      - planner_recommendations.json
      - impact_estimates.json
      - map_data.json
    """
    demand_results = run_demand_pipeline(
        "backend/input/patient_reports",
        "backend/output/data/demand_data.json",
    )
    supply_results = run_supply_pipeline(
        "backend/input/facility_docs",
        "backend/Virtue Foundation Ghana v0.3 - Sheet1.csv",
        "backend/output/data/supply_data.json",
    )

    deserts = detect_deserts(demand_results, supply_results)
    recommendations = generate_recommendations(deserts)
    impact_estimates = estimate_impact(deserts)
    map_points = _build_map_points(demand_results, supply_results, deserts)

    write_json("backend/output/data/gap_analysis.json", [d.model_dump() for d in deserts])
    write_json(
        "backend/output/data/planner_recommendations.json",
        [r.model_dump() for r in recommendations],
    )
    write_json(
        "backend/output/data/impact_estimates.json",
        [i.model_dump() for i in impact_estimates],
    )
    write_json("backend/output/data/map_data.json", [p.model_dump() for p in map_points])
    write_json(
        "backend/output/data/planner_engine.json",
        build_planner_response(
            {
                "region": deserts[0].region_name if deserts else "Region",
                "hotspots": [
                    {
                        "region": d.region_name,
                        "gap_score": d.gap_score,
                        "population_affected": d.demand_count * 60000,
                        "lat": d.lat,
                        "lng": d.lng,
                    }
                    for d in deserts
                ],
                "recommendations": [r.model_dump() for r in recommendations],
                "baseline_kpis": {
                    "demand_total": len(demand_results),
                    "avg_coverage": (
                        sum(item.coverage_score for item in supply_results)
                        / max(len(supply_results), 1)
                    ),
                    "total_population_underserved": sum(
                        d.demand_count * 60000 for d in deserts
                    ),
                    "avg_gap_score": (
                        sum(d.gap_score for d in deserts) / max(len(deserts), 1)
                    ),
                },
            },
            trace_id="pipeline",
        ),
    )


if __name__ == "__main__":
    run_full_analysis()
