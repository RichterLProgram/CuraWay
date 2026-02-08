from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.ai.llm_client import call_llm
from src.intelligence.gap_detection import detect_gaps


class DesertAnalyticsRequest(BaseModel):
    region: Optional[Dict[str, Any]] = None
    demands: List[Dict[str, Any]]
    supply: List[Dict[str, Any]]
    params: Dict[str, Any] = Field(default_factory=dict)


class DesertFacility(BaseModel):
    facility_id: str
    name: str
    distance_km: float
    coverage_score: float
    verdict: str


class DesertItem(BaseModel):
    desert_id: str
    desert_score: float = Field(ge=0, le=1)
    affected_demand_count: int
    dominant_missing_capability_codes: List[str] = Field(default_factory=list)
    nearest_viable_facilities: List[DesertFacility] = Field(default_factory=list)
    recommended_action_package: Dict[str, Any] = Field(default_factory=dict)
    map: Optional[Dict[str, Any]] = None
    explanation: str
    llm_explanation: Optional[str] = None
    llm_priority: Optional[str] = None


class DesertAnalyticsResponse(BaseModel):
    trace_id: str
    top_deserts: List[DesertItem] = Field(default_factory=list)
    summary: Dict[str, Any]


class DesertExplainDraft(BaseModel):
    explanation: str
    priority: str


DEFAULT_PARAMS = {
    "radius_km": 200,
    "threshold": 0.6,
    "top_k_deserts": 5,
    "top_k_facilities": 3,
}


def analyze_deserts(payload: Dict[str, Any], trace_id: str) -> Dict[str, Any]:
    request = DesertAnalyticsRequest.model_validate(payload)
    params = dict(DEFAULT_PARAMS)
    params.update(request.params or {})

    demand_results: List[Dict[str, Any]] = []
    for demand in request.demands:
        result = detect_gaps(demand, request.supply, params, trace_id=trace_id)
        if result.get("gaps"):
            gap = result["gaps"][0]
            gap["map"] = result.get("map")
            demand_results.append(gap)

    clusters = _cluster_demands(demand_results)
    desert_items: List[DesertItem] = []
    for key, items in clusters.items():
        desert_items.append(
            _build_desert_item(key, items, request.supply, params, trace_id=trace_id)
        )

    desert_items.sort(key=lambda item: item.desert_score, reverse=True)
    top_deserts = desert_items[: int(params["top_k_deserts"])]

    summary = {
        "total_demands": len(request.demands),
        "deserts_found": len(desert_items),
        "avg_desert_score": round(
            sum(item.desert_score for item in desert_items) / max(len(desert_items), 1), 3
        ),
    }

    response = DesertAnalyticsResponse(
        trace_id=trace_id,
        top_deserts=top_deserts,
        summary=summary,
    )
    return response.model_dump()


def _cluster_demands(gaps: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    clusters: Dict[str, List[Dict[str, Any]]] = {}
    for gap in gaps:
        map_data = gap.get("map", {})
        demand_point = map_data.get("demand_point", {})
        lat = demand_point.get("lat")
        lon = demand_point.get("lon")
        if lat is None or lon is None:
            key = "unknown"
        else:
            key = f"{round(float(lat) * 4) / 4:.2f}:{round(float(lon) * 4) / 4:.2f}"
        clusters.setdefault(key, []).append(gap)
    return clusters


def _build_desert_item(
    cluster_key: str,
    gaps: List[Dict[str, Any]],
    supply: List[Dict[str, Any]],
    params: Dict[str, Any],
    trace_id: str,
) -> DesertItem:
    affected = len(gaps)
    desert_score = _aggregate_desert_score(gaps)
    missing_codes = _top_missing_codes(gaps)
    nearest_facilities = _nearest_facilities(gaps, supply, params)
    package = _build_action_package(desert_score, gaps, nearest_facilities)
    map_snippet = _build_map_snippet(gaps, nearest_facilities)
    explanation = _build_explanation(desert_score, missing_codes)
    llm_explanation, llm_priority = _llm_desert_explain(
        desert_score,
        missing_codes,
        affected,
        nearest_facilities,
        trace_id=trace_id,
    )

    return DesertItem(
        desert_id=str(uuid.uuid4()),
        desert_score=desert_score,
        affected_demand_count=affected,
        dominant_missing_capability_codes=missing_codes,
        nearest_viable_facilities=nearest_facilities,
        recommended_action_package=package,
        map=map_snippet,
        explanation=explanation,
        llm_explanation=llm_explanation,
        llm_priority=llm_priority,
    )


def _aggregate_desert_score(gaps: List[Dict[str, Any]]) -> float:
    scores = [float(gap.get("desert_score", 0)) for gap in gaps]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


def _top_missing_codes(gaps: List[Dict[str, Any]], limit: int = 5) -> List[str]:
    counts: Dict[str, int] = {}
    for gap in gaps:
        for code in gap.get("missing_capabilities", []):
            counts[code] = counts.get(code, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [code for code, _ in ranked[:limit]]


def _nearest_facilities(
    gaps: List[Dict[str, Any]],
    supply: List[Dict[str, Any]],
    params: Dict[str, Any],
) -> List[DesertFacility]:
    facility_points: List[Dict[str, Any]] = []
    for gap in gaps:
        map_data = gap.get("map", {})
        facility_points.extend(map_data.get("facility_points", []))
    by_id: Dict[str, Dict[str, Any]] = {}
    for point in facility_points:
        facility_id = point.get("facility_id")
        if not facility_id:
            continue
        existing = by_id.get(facility_id)
        if not existing or point.get("coverage_score", 0) > existing.get("coverage_score", 0):
            by_id[facility_id] = point

    name_lookup = {item.get("facility_id"): item.get("name") for item in supply}
    facilities = [
        DesertFacility(
            facility_id=fid,
            name=name_lookup.get(fid, "Facility"),
            distance_km=float(point.get("distance_km", 0)),
            coverage_score=float(point.get("coverage_score", 0)),
            verdict=point.get("verdict", "plausible"),
        )
        for fid, point in by_id.items()
    ]
    facilities.sort(key=lambda item: (-item.coverage_score, item.distance_km))
    return facilities[: int(params.get("top_k_facilities", 3))]


def _build_action_package(
    desert_score: float,
    gaps: List[Dict[str, Any]],
    nearest_facilities: List[DesertFacility],
) -> Dict[str, Any]:
    if desert_score >= 0.7 or not nearest_facilities:
        return {
            "investment": "Invest in new capabilities and equipment package.",
            "staffing": "Recruit critical staff for missing capabilities.",
            "referral": "Establish referral pathways to regional hubs.",
        }
    if any(facility.verdict == "suspicious" for facility in nearest_facilities):
        return {
            "staffing": "Target staffing and training for existing facilities.",
            "equipment": "Upgrade essential equipment for capability gaps.",
            "referral": "Short-term referral while staffing is ramped up.",
        }
    return {
        "referral": "Route patients to nearest viable facilities.",
        "equipment": "Incremental equipment upgrades recommended.",
        "staffing": "Minor staffing support.",
    }


def _build_map_snippet(
    gaps: List[Dict[str, Any]],
    nearest_facilities: List[DesertFacility],
) -> Dict[str, Any]:
    first_map = gaps[0].get("map") if gaps else {}
    return {
        "demand_point": first_map.get("demand_point") if first_map else None,
        "facility_points": [item.model_dump() for item in nearest_facilities],
        "travel_time_bands": first_map.get("travel_time_bands") if first_map else None,
    }


def _build_explanation(desert_score: float, missing_codes: List[str]) -> str:
    if desert_score >= 0.7:
        return "High desert score with critical capability gaps."
    if missing_codes:
        return "Moderate desert score driven by missing core capabilities."
    return "Low desert score; coverage largely sufficient."


def _llm_desert_explain(
    desert_score: float,
    missing_codes: List[str],
    affected: int,
    nearest_facilities: List[DesertFacility],
    trace_id: str,
) -> tuple[Optional[str], Optional[str]]:
    prompt = (
        "Summarize this medical desert in 1-2 sentences and assign a priority "
        "(high/medium/low) for NGO action."
        "\n\nDesert score: "
        f"{desert_score}\n"
        f"Missing codes: {missing_codes}\n"
        f"Affected demand count: {affected}\n"
        f"Nearest facilities: {[item.model_dump() for item in nearest_facilities]}"
    )
    try:
        result = call_llm(
            prompt=prompt,
            schema=DesertExplainDraft,
            system_prompt="Return ONLY JSON for the schema.",
            trace_id=trace_id,
            step_id="desert_explanation",
            input_refs={
                "desert_score": desert_score,
                "missing_count": len(missing_codes),
                "affected": affected,
            },
            mock_key="desert_explain",
        )
        draft = result.parsed
        return draft.explanation, draft.priority
    except Exception:
        return None, None
