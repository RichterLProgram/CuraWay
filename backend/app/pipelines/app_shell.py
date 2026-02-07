"""Unified frontend shell output."""

from typing import Any, Dict, List


def build_app_shell(
    patient_results: List[object],
    analyst_api: Dict[str, Any],
) -> Dict[str, Any]:
    total_matches = sum(len(r.matches) for r in patient_results)
    return {
        "tabs": [
            {
                "id": "patient",
                "label": "Patient",
                "cta": "Upload report",
                "source": "patient_api.json",
            },
            {
                "id": "analyst",
                "label": "Analyst",
                "cta": "View coverage map",
                "source": "analyst_api.json",
            },
        ],
        "kpis": {
            "patient_searches": len(patient_results),
            "trial_matches": total_matches,
            "demand_points": len(analyst_api.get("pins", [])),
            "desert_regions": len(analyst_api.get("heatmap", [])),
        },
    }
