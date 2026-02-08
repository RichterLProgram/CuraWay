from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.geo.haversine import haversine_km
from src.ontology.normalize import normalize_capability_name
from src.shared.models import DesertScoreComponents, Evidence

DEFAULT_PREREQUISITES: Dict[str, List[str]] = {
    "ONC_GENERAL": ["PATHOLOGY", "IMAGING_CT"],
    "ONC_CHEMO": ["ONC_GENERAL", "PATHOLOGY"],
    "ONC_RADIOTHERAPY": ["ONC_GENERAL", "IMAGING_CT", "OXYGEN_SUPPLY"],
    "IMAGING_CT": ["SPECIALIST_RADIOLOGY"],
    "SURGERY_GENERAL": ["SURGERY_OT", "ANESTHESIA", "OXYGEN_SUPPLY"],
    "LAB_BLOODBANK": ["LAB_GENERAL"],
}


class FacilitySnapshot(BaseModel):
    facility_id: str
    name: Optional[str] = None
    location: Dict[str, Any]
    capabilities: List[Any] = Field(default_factory=list)
    equipment: List[Any] = Field(default_factory=list)
    specialists: List[Any] = Field(default_factory=list)
    canonical_capabilities: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    source_doc_id: Optional[str] = None


class DesertMetricSeed(BaseModel):
    facility_id: str
    region_id: Optional[str] = None
    capability_target: str
    distance_km_to_nearest_capable: Optional[float]
    facility_codes: List[str] = Field(default_factory=list)
    missing_prerequisites: List[str] = Field(default_factory=list)
    distance_component: float
    missing_prerequisites_component: float
    evidence: List[Evidence] = Field(default_factory=list)


def normalize_target(target: str) -> str:
    normalized = normalize_capability_name(target)
    code = normalized.get("code")
    return code or str(target).strip().upper()


def resolve_prerequisites(
    capability_target: str, mapping: Optional[Dict[str, List[str]]] = None
) -> List[str]:
    target = str(capability_target).strip().upper()
    prereqs = (mapping or DEFAULT_PREREQUISITES).get(target, [])
    return sorted({code for code in prereqs if code})


def compute_components(
    distance_km: float, missing_count: int, confidence: float
) -> DesertScoreComponents:
    distance_component = min(1.0, distance_km / 200.0) * 50.0
    missing_component = min(1.0, missing_count / 5.0) * 30.0
    data_incompleteness_component = (1.0 - confidence) * 20.0
    total = round(distance_component + missing_component + data_incompleteness_component)
    return DesertScoreComponents(
        distance_component=round(distance_component, 2),
        missing_prerequisites_component=round(missing_component, 2),
        data_incompleteness_component=round(data_incompleteness_component, 2),
        total_score=float(total),
    )


def build_desert_metric_seeds(
    facilities: Iterable[Dict[str, Any]],
    capability_target: str,
    region: Optional[Dict[str, Any]] = None,
    max_distance_km: float = 200.0,
    prerequisites_map: Optional[Dict[str, List[str]]] = None,
) -> List[DesertMetricSeed]:
    snapshots = [_coerce_facility(item) for item in facilities]
    region_filtered = [item for item in snapshots if _in_region(item, region)]
    target_code = normalize_target(capability_target)
    prerequisites = resolve_prerequisites(target_code, mapping=prerequisites_map)

    seeds: List[DesertMetricSeed] = []
    for facility in region_filtered:
        facility_codes = _facility_codes(facility)
        missing_prereqs = [code for code in prerequisites if code not in facility_codes]

        distance, nearest = _nearest_capable(
            facility, snapshots, target_code
        )
        distance_component = _distance_component(distance, max_distance_km)
        missing_component = _missing_component(len(missing_prereqs))

        evidence = _collect_evidence(
            facility, nearest, [target_code] + missing_prereqs
        )

        seeds.append(
            DesertMetricSeed(
                facility_id=facility.facility_id,
                region_id=_region_id(region, facility),
                capability_target=target_code,
                distance_km_to_nearest_capable=distance,
                facility_codes=facility_codes,
                missing_prerequisites=missing_prereqs,
                distance_component=distance_component,
                missing_prerequisites_component=missing_component,
                evidence=evidence,
            )
        )
    return seeds


def _distance_component(distance_km: Optional[float], max_distance_km: float) -> float:
    effective = max_distance_km if distance_km is None else float(distance_km)
    return round(min(1.0, effective / 200.0) * 50.0, 2)


def _missing_component(missing_count: int) -> float:
    return round(min(1.0, missing_count / 5.0) * 30.0, 2)


def _coerce_facility(raw: Dict[str, Any]) -> FacilitySnapshot:
    return FacilitySnapshot(
        facility_id=str(raw.get("facility_id") or ""),
        name=raw.get("name"),
        location=raw.get("location") or {},
        capabilities=list(raw.get("capabilities") or []),
        equipment=list(raw.get("equipment") or []),
        specialists=list(raw.get("specialists") or []),
        canonical_capabilities=list(raw.get("canonical_capabilities") or []),
        citations=list(raw.get("citations") or []),
        source_doc_id=raw.get("source_doc_id"),
    )


def _region_id(region: Optional[Dict[str, Any]], facility: FacilitySnapshot) -> Optional[str]:
    if not region:
        return None
    return region.get("region_id") or facility.location.get("region")


def _in_region(facility: FacilitySnapshot, region: Optional[Dict[str, Any]]) -> bool:
    if not region:
        return True
    bbox = region.get("bbox") or region.get("bounds")
    if bbox:
        lat = _loc_value(facility.location, "lat")
        lon = _loc_value(facility.location, "lon")
        if lat is None or lon is None:
            return False
        return (
            float(bbox.get("lat_min", -90)) <= lat <= float(bbox.get("lat_max", 90))
            and float(bbox.get("lon_min", -180)) <= lon <= float(bbox.get("lon_max", 180))
        )
    center = region.get("center") or region
    radius_km = region.get("radius_km")
    if center and radius_km is not None:
        lat = _loc_value(facility.location, "lat")
        lon = _loc_value(facility.location, "lon")
        if lat is None or lon is None:
            return False
        distance = haversine_km(
            float(center.get("lat")),
            float(center.get("lon") or center.get("lng")),
            lat,
            lon,
        )
        return distance <= float(radius_km)
    return True


def _loc_value(location: Dict[str, Any], key: str) -> Optional[float]:
    if key == "lon" and "lon" not in location and "lng" in location:
        key = "lng"
    value = location.get(key)
    if value is None:
        return None
    return float(value)


def _facility_codes(facility: FacilitySnapshot) -> List[str]:
    codes: List[str] = []
    for entry in facility.canonical_capabilities:
        if entry and entry not in codes:
            codes.append(entry)
    for entry in facility.capabilities + facility.equipment + facility.specialists:
        code = _entry_code(entry)
        if code and code not in codes:
            codes.append(code)
    return codes


def _entry_code(entry: Any) -> Optional[str]:
    if isinstance(entry, dict):
        code = entry.get("capability_code")
        name = entry.get("name")
    else:
        code = getattr(entry, "capability_code", None)
        name = getattr(entry, "name", None)
    if code:
        return str(code)
    if name:
        normalized = normalize_capability_name(str(name))
        return normalized.get("code")
    return None


def _nearest_capable(
    facility: FacilitySnapshot,
    all_facilities: List[FacilitySnapshot],
    target_code: str,
) -> Tuple[Optional[float], Optional[FacilitySnapshot]]:
    facility_codes = _facility_codes(facility)
    if target_code in facility_codes:
        return 0.0, facility

    lat = _loc_value(facility.location, "lat")
    lon = _loc_value(facility.location, "lon")
    if lat is None or lon is None:
        return None, None

    nearest_distance: Optional[float] = None
    nearest_facility: Optional[FacilitySnapshot] = None
    for candidate in all_facilities:
        candidate_codes = _facility_codes(candidate)
        if target_code not in candidate_codes:
            continue
        cand_lat = _loc_value(candidate.location, "lat")
        cand_lon = _loc_value(candidate.location, "lon")
        if cand_lat is None or cand_lon is None:
            continue
        distance = haversine_km(lat, lon, cand_lat, cand_lon)
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_facility = candidate

    return (round(nearest_distance, 2) if nearest_distance is not None else None), nearest_facility


def _collect_evidence(
    facility: FacilitySnapshot,
    nearest: Optional[FacilitySnapshot],
    target_codes: List[str],
) -> List[Evidence]:
    evidence: List[Evidence] = []
    evidence.extend(_facility_evidence(facility, target_codes))
    if not evidence and nearest and nearest.facility_id != facility.facility_id:
        evidence.extend(_facility_evidence(nearest, target_codes))
    if not evidence:
        evidence.append(
            Evidence(
                row_id=0,
                snippet="No row-level evidence available.",
            )
        )
    return evidence


def _facility_evidence(
    facility: FacilitySnapshot, target_codes: List[str]
) -> List[Evidence]:
    citation_lookup = {item.get("citation_id"): item for item in facility.citations or []}
    collected: List[Evidence] = []
    for entry in facility.capabilities + facility.equipment + facility.specialists:
        code = _entry_code(entry)
        if code and code not in target_codes:
            continue
        evidence = _entry_evidence(entry, citation_lookup, facility.source_doc_id)
        if evidence:
            collected.append(evidence)
    return collected


def _entry_evidence(
    entry: Any,
    citation_lookup: Dict[str, Dict[str, Any]],
    fallback_doc_id: Optional[str],
) -> Optional[Evidence]:
    if isinstance(entry, dict):
        evidence = entry.get("evidence") or {}
        citation_ids = entry.get("citation_ids") or []
        name = entry.get("name") or ""
    else:
        evidence = getattr(entry, "evidence", None) or {}
        citation_ids = getattr(entry, "citation_ids", None) or []
        name = getattr(entry, "name", "") or ""

    citation_id = str(citation_ids[0]) if citation_ids else None
    snippet = str(evidence.get("snippet") or name or "")
    row_id = evidence.get("source_row_id")
    column_name = evidence.get("source_column_name")
    source_doc_id = fallback_doc_id

    if citation_id and citation_lookup.get(citation_id):
        citation = citation_lookup[citation_id]
        source_doc_id = citation.get("source_doc_id") or source_doc_id
        locator = citation.get("locator") or {}
        row_id = locator.get("row", row_id)
        column_name = locator.get("col", column_name)
        snippet = citation.get("quote") or snippet

    if not snippet:
        return None

    return Evidence(
        citation_id=citation_id,
        source_doc_id=source_doc_id,
        row_id=row_id,
        column_name=column_name,
        snippet=snippet,
    )
