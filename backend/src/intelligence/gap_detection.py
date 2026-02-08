from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple

import yaml
from pydantic import BaseModel, Field

from src.ai.llm_client import call_llm
from src.ontology.normalize import normalize_capability_name
from src.geo.haversine import haversine_km
from src.geo.travel_time import build_travel_time_bands, estimate_travel_time_minutes
from src.shared.utils import infer_location


class Location(BaseModel):
    lat: float
    lon: float
    region: str


class Demand(BaseModel):
    diagnosis: str
    stage: Optional[str] = None
    biomarkers: List[str] = Field(default_factory=list)
    location: Location
    urgency: int = Field(ge=0, le=10)
    required_capabilities: List[str] = Field(default_factory=list)
    required_capability_codes: List[str] = Field(default_factory=list)


class SupplyFacility(BaseModel):
    facility_id: str
    name: str
    location: Location
    capabilities: List[Any] = Field(default_factory=list)
    validation: Optional[Dict[str, Any]] = None
    canonical_capabilities: List[str] = Field(default_factory=list)


class FacilityMatch(BaseModel):
    facility_id: str
    distance_km: float
    coverage_score: float = Field(ge=0, le=1)
    travel_time_min: Optional[int] = None
    notes: Optional[str] = None


class Gap(BaseModel):
    gap_id: str
    demand_id: str
    missing_capabilities: List[str] = Field(default_factory=list)
    candidate_facilities: List[FacilityMatch] = Field(default_factory=list)
    desert_score: float = Field(ge=0, le=1)
    rationale: str
    explanation: str
    llm_rationale: Optional[str] = None
    llm_explanation: Optional[str] = None
    llm_anomalies: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    type: Literal["route_patient", "refer", "invest", "staffing"]
    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    impacted_patients_estimate: Optional[int] = None
    geo: Optional[Location] = None


class GapExplainDraft(BaseModel):
    rationale: str
    explanation: str
    anomalies: List[str] = Field(default_factory=list)


DEFAULT_PARAMS = {
    "radius_km": 200,
    "top_k": 5,
    "threshold": 0.6,
}

DEFAULT_MAPPINGS = [
    {
        "match": "lung cancer",
        "capabilities": [
            "ONC_GENERAL",
            "IMAGING_CT",
            "PATHOLOGY",
            "SPECIALIST_RADIOLOGY",
        ],
    },
    {
        "match": "breast cancer",
        "capabilities": [
            "ONC_GENERAL",
            "IMAGING_XRAY",
            "IMAGING_ULTRASOUND",
            "PATHOLOGY",
        ],
    },
    {
        "match": "cervical cancer",
        "capabilities": [
            "ONC_GENERAL",
            "ONC_RADIOTHERAPY",
            "PATHOLOGY",
        ],
    },
]


def detect_gaps(
    demand_json: Dict[str, Any],
    supply_list_json: List[Dict[str, Any]],
    params: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    config = dict(DEFAULT_PARAMS)
    if params:
        config.update(params)

    demand, demand_id = _normalize_demand(demand_json)
    required = _normalize_required_codes(demand)

    facilities = [_normalize_supply_facility(item) for item in supply_list_json]
    speed_kmph = float(config.get("avg_speed_kmph") or os.getenv("AVG_SPEED_KMPH", "40"))
    candidates, best_facility, facility_points = _score_facilities(
        demand, facilities, required, config, speed_kmph
    )
    missing = _compute_missing(required, best_facility)

    desert_score = _compute_desert_score(
        demand.urgency, best_facility, candidates, config
    )
    rationale = _build_rationale(demand.urgency, best_facility, candidates, config)

    gap = Gap(
        gap_id=str(uuid.uuid4()),
        demand_id=demand_id,
        missing_capabilities=missing,
        candidate_facilities=candidates,
        desert_score=desert_score,
        rationale=rationale,
        explanation=_build_gap_explanation(desert_score, missing),
    )
    _apply_llm_gap_explanation(
        gap,
        demand,
        candidates,
        missing,
        desert_score,
        trace_id=trace_id,
    )

    recommendations = _build_recommendations(
        demand, desert_score, candidates, best_facility, config
    )

    travel_bands = build_travel_time_bands(
        facility_points, speed_kmph=speed_kmph
    )
    map_payload = {
        "demand_point": {
            "lat": demand.location.lat,
            "lon": demand.location.lon,
        },
        "facility_points": facility_points,
        "desert_polygons": [],
        "radius_km": config["radius_km"],
        "travel_time_bands": travel_bands,
        "legend": {
            "coverage_score": "0..1 relative coverage vs required capabilities",
            "verdict": "validation verdict (plausible/suspicious/impossible)",
            "travel_time_min": "approximate travel time in minutes",
        },
    }

    return {
        "gaps": [gap.model_dump()],
        "recommendations": [rec.model_dump() for rec in recommendations],
        "map": map_payload,
    }


def _normalize_demand(demand_json: Dict[str, Any]) -> Tuple[Demand, str]:
    profile = demand_json.get("profile", {})
    demand_id = (
        demand_json.get("demand_id")
        or profile.get("patient_id")
        or str(uuid.uuid4())
    )
    diagnosis = (
        demand_json.get("diagnosis")
        or profile.get("diagnosis")
        or "unknown"
    )
    stage = demand_json.get("stage") or profile.get("stage")
    biomarkers = demand_json.get("biomarkers") or profile.get("biomarkers") or []
    urgency = demand_json.get("urgency") or profile.get("urgency_score") or 5

    location_raw = (
        demand_json.get("location")
        or profile.get("location")
        or {"lat": 7.9465, "lng": -1.0232, "region": "Unknown"}
    )
    location = _normalize_location(location_raw)

    required = demand_json.get("required_capabilities") or demand_json.get("required")
    required_codes = demand_json.get("required_capability_codes") or []
    if not required and demand_json.get("profile"):
        required = demand_json.get("required_capabilities", [])
    if not required:
        required = _derive_required_capabilities(
            diagnosis, stage, biomarkers
        )

    return (
        Demand(
            diagnosis=diagnosis,
            stage=stage,
            biomarkers=biomarkers,
            location=location,
            urgency=int(urgency),
            required_capabilities=required,
            required_capability_codes=_normalize_code_list(required_codes),
        ),
        str(demand_id),
    )


def _normalize_supply_facility(item: Dict[str, Any]) -> SupplyFacility:
    location = _normalize_location(item.get("location", {}))
    return SupplyFacility(
        facility_id=str(item.get("facility_id") or ""),
        name=str(item.get("name") or ""),
        location=location,
        capabilities=_as_list(item.get("capabilities")),
        validation=item.get("validation"),
        canonical_capabilities=_normalize_code_list(
            item.get("canonical_capabilities") or item.get("capability_codes") or []
        ),
    )


def _normalize_location(raw: Any) -> Location:
    if isinstance(raw, str):
        lat, lng, region = infer_location(raw)
        return Location(lat=lat, lon=lng, region=region)

    if isinstance(raw, dict):
        lat = raw.get("lat")
        lon = raw.get("lon")
        if lon is None:
            lon = raw.get("lng")
        region = raw.get("region", "Unknown")
        if lat is None or lon is None:
            lat, lon, region = infer_location(region)
        return Location(lat=float(lat), lon=float(lon), region=str(region))

    lat, lon, region = infer_location("unknown")
    return Location(lat=lat, lon=lon, region=region)


def _derive_required_capabilities(
    diagnosis: str, stage: Optional[str], biomarkers: List[str]
) -> List[str]:
    mappings = _load_capability_mappings()
    diagnosis_norm = diagnosis.lower()
    derived: List[str] = []
    for entry in mappings:
        match = entry.get("match", "").lower()
        if match and match in diagnosis_norm:
            derived.extend(entry.get("capabilities", []))

    if "stage" in (stage or "").lower():
        derived.append("ONC_GENERAL")

    if not derived:
        derived = ["ONC_GENERAL", "IMAGING_XRAY"]

    return sorted(set(derived))


def _load_capability_mappings() -> List[Dict[str, Any]]:
    path = os.path.join(os.path.dirname(__file__), "capability_mappings.yaml")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            return data.get("mappings", DEFAULT_MAPPINGS)
        except (OSError, yaml.YAMLError):
            return DEFAULT_MAPPINGS
    return DEFAULT_MAPPINGS


def _normalize_code_list(codes: List[str]) -> List[str]:
    return sorted({code.strip() for code in codes if isinstance(code, str) and code.strip()})


def _normalize_required_codes(demand: Demand) -> List[str]:
    if demand.required_capability_codes:
        return _normalize_code_list(demand.required_capability_codes)
    codes: List[str] = []
    for cap in demand.required_capabilities:
        normalized = normalize_capability_name(str(cap))
        code = normalized.get("code")
        if code and code not in codes:
            codes.append(code)
    return codes


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [item for item in value if item is not None]
    if isinstance(value, str):
        return [value]
    return []


def _score_facilities(
    demand: Demand,
    facilities: List[SupplyFacility],
    required: List[str],
    config: Dict[str, Any],
    speed_kmph: float,
) -> Tuple[List[FacilityMatch], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    threshold = float(config["threshold"])
    top_k = int(config["top_k"])
    radius_km = float(config["radius_km"])

    scored: List[Dict[str, Any]] = []
    facility_points: List[Dict[str, Any]] = []

    for facility in facilities:
        verdict = (
            (facility.validation or {}).get("verdict", "plausible")
            if facility.validation
            else "plausible"
        )
        validation_weight = _validation_weight(verdict)

        facility_caps = _extract_facility_codes(facility)
        if required:
            met = len(set(required) & set(facility_caps))
            coverage = (met / len(required)) * validation_weight
        else:
            coverage = 0.0

        distance = haversine_km(
            demand.location.lat,
            demand.location.lon,
            facility.location.lat,
            facility.location.lon,
        )
        travel_time_min = estimate_travel_time_minutes(distance, speed_kmph=speed_kmph)

        facility_points.append(
            {
                "facility_id": facility.facility_id,
                "lat": facility.location.lat,
                "lon": facility.location.lon,
                "distance_km": round(distance, 2),
                "travel_time_min": travel_time_min,
                "coverage_score": round(coverage, 3),
                "verdict": verdict,
            }
        )

        scored.append(
            {
                "facility": facility,
                "coverage": coverage,
                "distance": distance,
                "verdict": verdict,
                "facility_caps": facility_caps,
                "travel_time_min": travel_time_min,
            }
        )

    scored.sort(
        key=lambda item: (-item["coverage"], item["distance"])
    )

    candidates: List[FacilityMatch] = []
    best_facility: Optional[Dict[str, Any]] = scored[0] if scored else None

    for entry in scored:
        if entry["verdict"] == "impossible":
            continue
        if entry["coverage"] <= threshold:
            continue
        if entry["distance"] > radius_km:
            continue
        facility = entry["facility"]
        candidates.append(
            FacilityMatch(
                facility_id=facility.facility_id,
                distance_km=round(entry["distance"], 2),
                coverage_score=round(entry["coverage"], 3),
                travel_time_min=entry.get("travel_time_min"),
                notes=None,
            )
        )
        if len(candidates) >= top_k:
            break

    return candidates, best_facility, facility_points


def _compute_missing(
    required: List[str], best_facility: Optional[Dict[str, Any]]
) -> List[str]:
    if not required:
        return []
    if not best_facility:
        return required

    facility_caps = best_facility.get("facility_caps", [])
    missing = sorted(set(required) - set(facility_caps))
    return missing


def _compute_desert_score(
    urgency: int,
    best_facility: Optional[Dict[str, Any]],
    candidates: List[FacilityMatch],
    config: Dict[str, Any],
) -> float:
    urgency_factor = min(1.0, max(0.0, urgency / 10))
    if candidates:
        best_coverage = candidates[0].coverage_score
        return round(max(0.0, (1 - best_coverage) * 0.5 * urgency_factor), 3)
    if best_facility and best_facility.get("verdict") != "impossible":
        best_coverage = float(best_facility.get("coverage", 0))
        return round(min(1.0, 0.4 + (1 - best_coverage) * 0.4 + 0.2 * urgency_factor), 3)
    return round(min(1.0, 0.6 + 0.4 * urgency_factor), 3)


def _build_rationale(
    urgency: int,
    best_facility: Optional[Dict[str, Any]],
    candidates: List[FacilityMatch],
    config: Dict[str, Any],
) -> str:
    if candidates:
        return "Suitable facility found within radius."
    if best_facility and best_facility.get("verdict") != "impossible":
        return "Facilities exist but do not meet coverage threshold."
    if urgency >= 8:
        return "High urgency with no viable facilities in radius."
    return "Limited coverage for required capabilities."


def _build_gap_explanation(desert_score: float, missing: List[str]) -> str:
    if desert_score >= 0.7:
        return "High desert score with significant capability gaps."
    if missing:
        return "Some required capabilities are missing nearby."
    return "Coverage appears adequate within radius."


def _apply_llm_gap_explanation(
    gap: Gap,
    demand: Demand,
    candidates: List[FacilityMatch],
    missing: List[str],
    desert_score: float,
    trace_id: Optional[str],
) -> None:
    prompt = (
        "Provide a concise rationale and explanation for the gap detection result. "
        "Highlight anomalies or inconsistencies if present."
        "\n\nDemand:\n"
        f"{demand.model_dump()}\n\n"
        f"Candidates: {[item.model_dump() for item in candidates]}\n"
        f"Missing capabilities: {missing}\n"
        f"Desert score: {desert_score}"
    )
    try:
        result = call_llm(
            prompt=prompt,
            schema=GapExplainDraft,
            system_prompt="Return ONLY JSON for the schema.",
            trace_id=trace_id,
            step_id="gap_explanation",
            input_refs={
                "missing_count": len(missing),
                "candidate_count": len(candidates),
                "desert_score": desert_score,
            },
            mock_key="gap_explain",
        )
        draft = result.parsed
        gap.llm_rationale = draft.rationale
        gap.llm_explanation = draft.explanation
        gap.llm_anomalies = draft.anomalies or []
    except Exception:
        gap.llm_rationale = gap.rationale
        gap.llm_explanation = gap.explanation


def _build_recommendations(
    demand: Demand,
    desert_score: float,
    candidates: List[FacilityMatch],
    best_facility: Optional[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Recommendation]:
    recommendations: List[Recommendation] = []

    if candidates:
        recommendations.append(
            Recommendation(
                type="route_patient",
                title="Route patient to best facility",
                description="Route to the highest coverage facility within radius.",
                priority="medium",
                impacted_patients_estimate=1,
                geo=demand.location,
            )
        )
        return recommendations

    if desert_score >= 0.7:
        recommendations.append(
            Recommendation(
                type="invest",
                title="Invest in local capability expansion",
                description="No facility meets minimum coverage within radius.",
                priority="high",
                impacted_patients_estimate=1,
                geo=demand.location,
            )
        )
        return recommendations

    if best_facility and best_facility.get("verdict") != "impossible":
        recommendations.append(
            Recommendation(
                type="staffing",
                title="Staffing or equipment uplift",
                description="Closest facilities lack key capabilities.",
                priority="medium",
                impacted_patients_estimate=1,
                geo=demand.location,
            )
        )
        return recommendations

    recommendations.append(
        Recommendation(
            type="refer",
            title="Refer to distant facility",
            description="Consider referral outside of standard radius.",
            priority="low",
            impacted_patients_estimate=1,
            geo=demand.location,
        )
    )
    return recommendations


def _extract_facility_codes(facility: SupplyFacility) -> List[str]:
    codes: List[str] = []
    for code in facility.canonical_capabilities:
        if code not in codes:
            codes.append(code)
    for entry in facility.capabilities:
        if isinstance(entry, dict) and entry.get("capability_code"):
            code = entry.get("capability_code")
            if code and code not in codes:
                codes.append(code)
            continue
        if hasattr(entry, "capability_code") and getattr(entry, "capability_code"):
            code = getattr(entry, "capability_code")
            if code and code not in codes:
                codes.append(code)
            continue
        normalized = normalize_capability_name(str(entry))
        code = normalized.get("code")
        if code and code not in codes:
            codes.append(code)
    return codes


def _validation_weight(verdict: str) -> float:
    if verdict == "plausible":
        return 1.0
    if verdict == "suspicious":
        return 0.7
    if verdict == "impossible":
        return 0.0
    return 0.7


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
