from __future__ import annotations

from typing import Any, Dict, List


def optimize_policy(payload: Dict[str, Any]) -> Dict[str, Any]:
    constraints = payload.get("constraints", {}) or {}
    budget = float(constraints.get("budget", 1_000_000))
    staff = int(constraints.get("staff", 50))
    max_travel = int(constraints.get("max_travel_minutes", 180))

    options: List[Dict[str, Any]] = []
    for idx, weight in enumerate([0.8, 1.0, 1.2], start=1):
        option_budget = round(budget * weight)
        coverage_gain = round(8 + idx * 6 + (staff / 25), 1)
        underserved_reduction = int(40 + idx * 15 + staff / 2)
        travel_improvement = max(10, max_travel - idx * 15)
        options.append(
            {
                "id": f"policy-{idx}",
                "label": f"Policy Option {idx}",
                "budget": option_budget,
                "staff": staff + idx * 5,
                "coverage_gain_pct": coverage_gain,
                "underserved_reduction_k": underserved_reduction,
                "avg_travel_minutes": travel_improvement,
                "tradeoffs": [
                    "Higher upfront capex",
                    "Requires regional staffing approval",
                    "Supply chain lead time 6-8 weeks",
                ],
            }
        )

    options.sort(key=lambda item: (-item["coverage_gain_pct"], item["avg_travel_minutes"]))
    return {"options": options}
