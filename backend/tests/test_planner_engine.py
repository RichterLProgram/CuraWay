import os

from src.intelligence.planner_engine import build_planner_response


def test_planner_engine_response_shape():
    os.environ["LLM_DISABLED"] = "true"
    payload = {
        "region": "North",
        "hotspots": [
            {
                "region": "North",
                "gap_score": 0.72,
                "population_affected": 120000,
                "lat": 5.1,
                "lng": -0.2,
            },
            {
                "region": "East",
                "gap_score": 0.6,
                "population_affected": 80000,
                "lat": 5.3,
                "lng": -0.1,
            },
        ],
        "recommendations": [
            {
                "region": "North",
                "action": "Upgrade diagnostics",
                "capability_needed": "IMAGING_CT",
            }
        ],
        "baseline_kpis": {
            "demand_total": 20,
            "avg_coverage": 42,
            "total_population_underserved": 120000,
            "avg_gap_score": 0.68,
        },
    }
    result = build_planner_response(payload, trace_id="trace-plan-1")
    assert result["summary"]
    assert result["hotspots"]
    assert result["action_plan"]["region"] == "North"
    assert "simulation_presets" in result
    assert set(result["simulation_presets"].keys()) == {
        "Low",
        "Balanced",
        "Aggressive",
    }
