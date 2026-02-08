from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.analytics.desert_explainer import explain_desert
from src.analytics.desert_metrics import (
    build_desert_metric_seeds,
    compute_components,
    normalize_target,
    resolve_prerequisites,
)
from src.observability.tracing import trace_event
from src.shared.models import DesertScore


class DesertScoreRequest(BaseModel):
    capability_target: str
    facilities: List[Dict[str, Any]] = Field(default_factory=list)
    supply: List[Dict[str, Any]] = Field(default_factory=list)
    region: Optional[Dict[str, Any]] = None
    max_distance_km: float = Field(default=200.0, ge=0)


def score_deserts(payload: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
    request = DesertScoreRequest.model_validate(payload)
    facilities = request.facilities or request.supply
    seeds = build_desert_metric_seeds(
        facilities=facilities,
        capability_target=request.capability_target,
        region=request.region,
        max_distance_km=request.max_distance_km,
    )

    scores: List[DesertScore] = []
    for seed in seeds:
        step_id = f"desert_explain_{seed.facility_id or uuid.uuid4()}"
        explain = explain_desert(
            capability_target=request.capability_target,
            suggested_target=seed.capability_target,
            missing_prerequisites=seed.missing_prerequisites,
            distance_km_to_nearest_capable=seed.distance_km_to_nearest_capable,
            evidence=seed.evidence,
            trace_id=trace_id,
            step_id=step_id,
        )
        normalized_target = (
            explain.normalized_target or seed.capability_target
        )
        normalized_target = normalize_target(normalized_target)
        if normalized_target != seed.capability_target:
            prereqs = resolve_prerequisites(normalized_target)
            missing_prereqs = [
                code for code in prereqs if code not in seed.facility_codes
            ]
        else:
            missing_prereqs = seed.missing_prerequisites

        components = compute_components(
            distance_km=seed.distance_km_to_nearest_capable or request.max_distance_km,
            missing_count=len(missing_prereqs),
            confidence=explain.confidence,
        )
        score = DesertScore(
            facility_id=seed.facility_id,
            region_id=seed.region_id,
            capability_target=normalized_target,
            distance_km_to_nearest_capable=seed.distance_km_to_nearest_capable,
            missing_prerequisites=missing_prereqs,
            coverage_gap_score=components.total_score,
            confidence=explain.confidence,
            subscores=components,
            evidence=seed.evidence,
            explanation=explain.explanation,
            step_trace_id=step_id,
        )
        scores.append(score)

    trace_event(
        trace_id,
        "desert_score",
        inputs_ref={
            "facility_count": len(facilities),
            "capability_target": request.capability_target,
        },
        outputs_ref={"score_count": len(scores)},
    )

    return {"trace_id": trace_id, "scores": [item.model_dump() for item in scores]}
