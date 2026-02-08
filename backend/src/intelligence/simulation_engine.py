from __future__ import annotations

from typing import Any, Dict, List


def generate_presets(
    baseline_kpis: Dict[str, Any],
    hotspots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    avg_gap = float(baseline_kpis.get("avg_gap_score", 0))
    underserved = int(baseline_kpis.get("total_population_underserved", 0))
    coverage = float(baseline_kpis.get("avg_coverage", 0))

    scenario_factors = {
        "Low": 0.4,
        "Balanced": 0.7,
        "Aggressive": 1.0,
    }

    presets: Dict[str, Any] = {}
    for name, factor in scenario_factors.items():
        coverage_delta = int(round(10 + (avg_gap * 40 * factor)))
        underserved_delta = int(round((underserved / 1000) * factor))
        roi_years = max(1.2, 4.0 - (avg_gap * 2.0 * factor))

        demand_impact = _build_demand_curve(coverage_delta)
        coverage_shift = _build_coverage_shift(coverage, coverage_delta, hotspots)
        cost_curve = {
            "cost": int(round((300 + coverage_delta * 8) * factor)),
            "impact": int(round(12 + coverage_delta * 0.6)),
        }

        presets[name] = {
            "coverage_delta": coverage_delta,
            "underserved_delta": -underserved_delta,
            "roi_window": f"{roi_years:.1f} yrs",
            "demand_impact": demand_impact,
            "coverage_shift": coverage_shift,
            "cost_curve": cost_curve,
        }

    return presets


def _build_demand_curve(coverage_delta: int) -> List[Dict[str, Any]]:
    baseline = [100, 102, 104, 106, 108, 110]
    drop = max(4, int(round(coverage_delta * 0.4)))
    curve = []
    for idx, value in enumerate(baseline, start=1):
        curve.append(
            {
                "month": f"M{idx}",
                "baseline": value,
                "simulated": max(40, value - drop - idx),
            }
        )
    return curve


def _build_coverage_shift(
    baseline_coverage: float,
    coverage_delta: int,
    hotspots: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    regions = [item.get("region") for item in hotspots if item.get("region")] or [
        "North",
        "Central",
        "East",
        "South",
    ]
    shift = []
    baseline = max(20, min(80, int(round(baseline_coverage or 50))))
    uplift = max(6, int(round(coverage_delta * 0.5)))
    for region in regions[:4]:
        shift.append(
            {
                "region": region,
                "baseline": baseline,
                "simulated": min(95, baseline + uplift),
            }
        )
    return shift
