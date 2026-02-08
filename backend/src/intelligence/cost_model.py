from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostEstimate:
    estimated_cost: str
    capex_cost: str
    opex_cost: str
    roi_window: str


def estimate_costs(gap_score: float, population_affected: int) -> CostEstimate:
    severity = max(0.1, min(1.0, gap_score))
    population_factor = max(1.0, population_affected / 50000.0)
    base_total = 250000 * (0.8 + severity) * population_factor
    low = int(base_total * 0.85)
    high = int(base_total * 1.15)
    capex = int(base_total * 0.7)
    opex = int(base_total * 0.3)
    roi_years = max(1.4, 4.5 - 2.5 * severity)

    return CostEstimate(
        estimated_cost=_format_range(low, high),
        capex_cost=_format_money(capex),
        opex_cost=f"{_format_money(opex)}/yr",
        roi_window=f"{roi_years:.1f} yrs",
    )


def _format_money(value: int) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value}"


def _format_range(low: int, high: int) -> str:
    return f"{_format_money(low)}–{_format_money(high)}"
