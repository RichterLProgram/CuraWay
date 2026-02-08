from __future__ import annotations

from typing import Any, Dict, List


def rank_hotspots(hotspots: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    if not hotspots:
        return []
    max_pop = max(int(item.get("population_affected", 0)) for item in hotspots) or 1

    def score(item: Dict[str, Any]) -> float:
        gap = float(item.get("gap_score", 0))
        population = int(item.get("population_affected", 0)) / max_pop
        return gap * 0.7 + population * 0.3

    ranked = sorted(hotspots, key=score, reverse=True)
    return ranked[:limit]
