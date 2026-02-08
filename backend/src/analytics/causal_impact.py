from __future__ import annotations

from statistics import mean, pstdev
from typing import Dict, List


def estimate_causal_impact(baseline: List[float], post: List[float]) -> Dict[str, float]:
    if not baseline or not post:
        return {
            "effect": 0.0,
            "uplift_pct": 0.0,
            "confidence_low": 0.0,
            "confidence_high": 0.0,
            "confidence": 0.0,
        }

    base_mean = mean(baseline)
    post_mean = mean(post)
    effect = post_mean - base_mean
    uplift_pct = (effect / base_mean) * 100 if base_mean else 0.0

    baseline_std = pstdev(baseline) if len(baseline) > 1 else 0.0
    post_std = pstdev(post) if len(post) > 1 else 0.0
    pooled_std = max(1.0, (baseline_std + post_std) / 2)
    confidence = min(0.95, max(0.35, 1 - pooled_std / max(abs(effect), 1.0)))

    margin = abs(effect) * (1 - confidence)
    return {
        "effect": round(effect, 2),
        "uplift_pct": round(uplift_pct, 2),
        "confidence_low": round(effect - margin, 2),
        "confidence_high": round(effect + margin, 2),
        "confidence": round(confidence, 2),
    }
