from __future__ import annotations

import csv
import json
import os
import sys
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

try:
    from fastapi import FastAPI, Request as FastAPIRequest
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except Exception:  # pragma: no cover - allow import in minimal envs
    FastAPI = None  # type: ignore[assignment]
    FastAPIRequest = object  # type: ignore[assignment]

    class _DummyResponse:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return

    FileResponse = _DummyResponse  # type: ignore[assignment]
    JSONResponse = _DummyResponse  # type: ignore[assignment]

    class StaticFiles:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return
from flask import Flask, jsonify, request
try:
    from starlette.exceptions import HTTPException as StarletteHTTPException
    from starlette.middleware.wsgi import WSGIMiddleware
except Exception:  # pragma: no cover - allow import in minimal envs
    class StarletteHTTPException(Exception):  # type: ignore
        status_code = 500

        def __init__(self, detail: Any = None, status_code: int | None = None) -> None:
            super().__init__(detail)
            if status_code is not None:
                self.status_code = status_code

    class WSGIMiddleware:  # type: ignore
        def __init__(self, app: Any) -> None:
            self.app = app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
STATIC_DIR = PROJECT_ROOT / "static"
INDEX_FILE = STATIC_DIR / "index.html"

def _demo_mode_enabled() -> bool:
    return os.getenv("DEMO_MODE", "1").lower() not in ("0", "false", "no")


def _lazy_import(module: str, name: str):
    try:
        imported = __import__(module, fromlist=[name])
        return getattr(imported, name)
    except Exception:
        return None


def _create_trace_id() -> str:
    fn = _lazy_import("src.observability.tracing", "create_trace_id")
    if fn is not None:
        return fn()
    return str(uuid.uuid4())


def _trace_event(*args: Any, **kwargs: Any) -> None:
    fn = _lazy_import("src.observability.tracing", "trace_event")
    if fn is None:
        return
    try:
        fn(*args, **kwargs)
    except Exception:
        return


def _read_trace(trace_id: str) -> List[Dict[str, Any]]:
    fn = _lazy_import("src.observability.tracing", "read_trace")
    if fn is None:
        return []
    try:
        return fn(trace_id)
    except Exception:
        return []


def _get_trace_steps(trace_id: str) -> List[Dict[str, Any]]:
    fn = _lazy_import("src.observability.trace_store", "get_trace_steps")
    if fn is None:
        return []
    try:
        return fn(trace_id)
    except Exception:
        return []


def _log_trace(*args: Any, **kwargs: Any) -> bool:
    fn = _lazy_import("src.observability.mlflow_logger", "log_trace")
    if fn is None:
        return False
    try:
        return bool(fn(*args, **kwargs))
    except Exception:
        return False


app = Flask(__name__)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
if not INDEX_FILE.exists():
    INDEX_FILE.write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\"/>"
        "<title>Demo is live</title></head>"
        "<body><h1>Demo is live</h1><p>CancerCompass demo is running.</p></body>"
        "</html>",
        encoding="utf-8",
    )

DATA_DIR = PROJECT_ROOT / "output" / "data"
VIRTUE_CSV_PATH = PROJECT_ROOT / "Virtue Foundation Ghana v0.3 - Sheet1.csv"


def load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_capability(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def parse_region(location: str) -> str:
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[-2].replace("Region", "").strip()
    return location.strip() or "Unknown"


def _load_virtue_rows() -> List[Dict[str, Any]]:
    if not VIRTUE_CSV_PATH.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with VIRTUE_CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append({key: (value or "").strip() for key, value in row.items()})
    return rows


def _parse_list_field(raw: str) -> List[str]:
    if not raw or raw.lower() == "null":
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except Exception:
        pass
    return [part.strip() for part in raw.split(",") if part.strip()]


REGION_COORDS = {
    "Accra": (5.6037, -0.1870),
    "Greater Accra": (5.6037, -0.1870),
    "Ashanti": (6.6891, -1.6244),
    "Western": (4.9434, -1.7055),
    "Central": (5.1053, -1.2466),
    "Eastern": (6.2, -0.27),
    "Volta": (6.6, 0.47),
    "Northern": (9.4, -1.0),
    "Upper East": (10.8, -0.9),
    "Upper West": (10.0, -2.5),
    "Brong Ahafo": (7.5, -2.5),
    "Bono": (7.9, -2.6),
    "Ahafo": (7.0, -2.7),
    "Bono East": (7.8, -1.3),
    "Oti": (8.2, 0.8),
    "North East": (10.5, -0.6),
    "Savannah": (9.6, -1.8),
    "Western North": (6.7, -2.5),
    "Takoradi": (4.8845, -1.7554),
    "Kumasi": (6.6885, -1.6244),
    "Tamale": (9.4075, -0.8536),
    "Cape Coast": (5.1053, -1.2466),
    "Ho": (6.6008, 0.4727),
    "KEEA": (5.0919, -1.0419),  # Ankaful, KEEA District, Central Region
    "Ankaful": (5.0919, -1.0419),
}


def _region_coords(name: str) -> tuple[float, float]:
    if not name or name.lower() in ("null", "none", "unknown"):
        return (7.95, -1.03)  # Center of Ghana
    key = name.strip()
    if key in REGION_COORDS:
        return REGION_COORDS[key]
    if key.title() in REGION_COORDS:
        return REGION_COORDS[key.title()]
    if key.upper() in REGION_COORDS:
        return REGION_COORDS[key.upper()]
    # Generate consistent coordinates within Ghana's bounds
    seed = sum(ord(char) for char in key)
    lat = 5.0 + (seed % 550) / 100  # 5.0 to 10.5
    lng = -3.0 + (seed % 300) / 100  # -3.0 to 0.0
    return (lat, lng)


def _jitter_coords(lat: float, lng: float, seed: int) -> tuple[float, float]:
    offset_lat = ((seed % 10) - 5) / 200
    offset_lng = (((seed // 3) % 10) - 5) / 200
    return (lat + offset_lat, lng + offset_lng)


CITY_REGION_MAP = {
    "accra": "Greater Accra",
    "osu": "Greater Accra",
    "dansoman": "Greater Accra",
    "cantonments": "Greater Accra",
    "tamale": "Northern",
    "kumasi": "Ashanti",
    "takoradi": "Western",
    "cape coast": "Central",
    "ho": "Volta",
    "koforidua": "Eastern",
    "sunyani": "Bono",
    "wa": "Upper West",
    "bolgatanga": "Upper East",
}


def _normalize_region(raw_region: str, raw_city: str) -> str:
    # Handle null/empty regions
    region = (raw_region or "").strip()
    if region and region.lower() not in ("null", "none", ""):
        # Special case: KEEA is a district in Central Region
        if region.upper() == "KEEA":
            return "KEEA"
        return region
    
    # Try to infer from city
    city = (raw_city or "").strip().lower()
    if not city or city in ("null", "none"):
        return "Unknown"
    
    # Check if city name contains KEEA
    if "keea" in city or "ankaful" in city:
        return "KEEA"
    
    # Check city mapping
    for key, mapped_region in CITY_REGION_MAP.items():
        if key in city:
            return mapped_region
    
    # Return city name if it's valid
    city_proper = (raw_city or "").strip()
    if city_proper and city_proper.lower() not in ("null", "none"):
        return city_proper
    
    return "Unknown"


def _coverage_from_type(facility_type: str, specialties: List[str]) -> int:
    base = {
        "hospital": 80,
        "clinic": 60,
        "pharmacy": 50,
        "doctor": 65,
        "dentist": 55,
    }.get(facility_type.lower(), 55)
    return min(95, base + len(specialties) * 3)


def _safe_int(value: Any, fallback: int) -> int:
    if value is None:
        return fallback
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    if not text or text == "null":
        return fallback
    try:
        return int(float(text))
    except Exception:
        return fallback


def build_demand_data() -> Dict[str, Any]:
    virtue_rows = _load_virtue_rows()
    if virtue_rows:
        region_counts: Dict[str, int] = {}
        for row in virtue_rows:
            raw_region = row.get("address_stateOrRegion", "")
            raw_city = row.get("address_city", "")
            region = _normalize_region(raw_region, raw_city)
            # Debug: Log first few null regions
            if region == "Unknown" and not getattr(build_demand_data, '_logged', False):
                print(f"DEBUG: null/unknown region - raw_region={raw_region!r}, raw_city={raw_city!r}, normalized={region!r}")
                build_demand_data._logged = True
            region_counts[region] = region_counts.get(region, 0) + 1

        points = []
        base_date = datetime.utcnow().date()
        diagnosis_counts: Counter[str] = Counter()
        idx = 0
        for region, supply_count in region_counts.items():
            base = 8 + (region_counts[region] % 12)
            demand_count = max(5, int(base + max(0, 10 - supply_count / 6)))
            lat, lng = _region_coords(region)
            for offset in range(demand_count):
                point_lat, point_lng = _jitter_coords(lat, lng, offset + idx)
                intensity = min(1.0, max(0.2, 0.9 - supply_count * 0.01))
                diagnosis = "General Oncology"
                diagnosis_counts[diagnosis] += 1
                points.append(
                    {
                        "id": f"D-{idx + 1}",
                        "lat": point_lat,
                        "lng": point_lng,
                        "intensity": intensity,
                        "diagnosis": diagnosis,
                        "urgency": min(10, 4 + int(intensity * 6)),
                        "region": region,
                        "date": (base_date - timedelta(days=idx)).isoformat(),
                    }
                )
                idx += 1

        top_diagnoses = [
            {"name": name, "count": count}
            for name, count in diagnosis_counts.most_common(5)
        ]
        return {
            "total_count": len(points),
            "points": points,
            "top_diagnoses": top_diagnoses,
        }

    demand_entries = load_json("demand_data.json")
    map_entries = load_json("map_data.json")
    demand_map: Dict[str, Dict[str, Any]] = {}
    for entry in map_entries:
        label = entry.get("label", "")
        if label.startswith("Demand:"):
            demand_map[label.split("Demand:", 1)[1]] = entry

    base_date = datetime.utcnow().date()
    points = []
    diagnosis_counts: Counter[str] = Counter()

    for idx, entry in enumerate(demand_entries):
        profile = entry.get("profile", {})
        patient_id = profile.get("patient_id", f"D-{idx + 1}")
        map_point = demand_map.get(patient_id, {})

        diagnosis = profile.get("diagnosis", "Unknown")
        diagnosis_counts[diagnosis] += 1

        urgency = int(profile.get("urgency_score", 5))
        intensity = float(
            map_point.get("intensity", min(1.0, max(0.1, urgency / 10)))
        )

        points.append(
            {
                "id": patient_id,
                "lat": float(map_point.get("lat", 0.0)),
                "lng": float(map_point.get("lng", 0.0)),
                "intensity": intensity,
                "diagnosis": diagnosis,
                "urgency": urgency,
                "region": parse_region(profile.get("location", "")),
                "date": (base_date - timedelta(days=idx)).isoformat(),
            }
        )

    top_diagnoses = [
        {"name": name, "count": count}
        for name, count in diagnosis_counts.most_common(5)
    ]

    return {
        "total_count": len(demand_entries),
        "points": points,
        "top_diagnoses": top_diagnoses,
    }


def build_supply_data() -> Dict[str, Any]:
    virtue_rows = _load_virtue_rows()
    if virtue_rows:
        facilities = []
        capability_counts: Counter[str] = Counter()
        coverage_total = 0.0
        for idx, row in enumerate(virtue_rows):
            name = row.get("name") or f"Facility {idx + 1}"
            facility_type = (row.get("facilityTypeId") or "facility").lower()
            specialties = _parse_list_field(row.get("specialties", ""))
            procedures = _parse_list_field(row.get("procedure", ""))
            equipment = _parse_list_field(row.get("equipment", ""))
            capabilities = _parse_list_field(row.get("capability", ""))
            capability_list = [format_capability(item) for item in (specialties + procedures + equipment + capabilities)]
            coverage = _coverage_from_type(facility_type, specialties)
            coverage_total += coverage
            capability_counts.update(capability_list)
            region = _normalize_region(
                row.get("address_stateOrRegion", ""),
                row.get("address_city", ""),
            )
            lat, lng = _region_coords(region)
            lat, lng = _jitter_coords(lat, lng, idx)
            facilities.append(
                {
                    "id": row.get("unique_id") or row.get("pk_unique_id") or f"f-{idx + 1}",
                    "name": name,
                    "lat": lat,
                    "lng": lng,
                    "type": facility_type.title(),
                    "capabilities": capability_list,
                    "coverage": int(round(coverage)),
                    "beds": _safe_int(row.get("capacity"), int(40 + coverage * 3)),
                    "staff": _safe_int(row.get("numberDoctors"), int(60 + coverage * 4)),
                    "region": region,
                }
            )
        total_count = len(facilities)
        avg_coverage = int(round(coverage_total / total_count)) if total_count else 0
        top_capabilities = [
            {"name": name, "count": count}
            for name, count in capability_counts.most_common(6)
        ]
        return {
            "total_count": total_count,
            "avg_coverage": avg_coverage,
            "facilities": facilities,
            "top_capabilities": top_capabilities,
        }

    supply_entries = load_json("supply_data.json")
    facilities = []
    capability_counts: Counter[str] = Counter()
    coverage_total = 0.0

    for idx, entry in enumerate(supply_entries):
        location = entry.get("location", {})
        name = entry.get("name", "Facility")
        coverage = float(entry.get("coverage_score", 0.0))
        coverage_total += coverage

        lower_name = name.lower()
        if "hospital" in lower_name:
            facility_type = "Hospital"
        elif "clinic" in lower_name:
            facility_type = "Clinic"
        else:
            facility_type = "Facility"

        capabilities = [format_capability(c) for c in entry.get("capabilities", [])]
        capability_counts.update(capabilities)

        facilities.append(
            {
                "id": entry.get("facility_id", f"f-{idx + 1}"),
                "name": name,
                "lat": float(location.get("lat", 0.0)),
                "lng": float(location.get("lng", 0.0)),
                "type": facility_type,
                "capabilities": capabilities,
                "coverage": int(round(coverage)),
                "beds": int(50 + coverage * 8),
                "staff": int(80 + coverage * 12),
                "region": location.get("region", "Unknown"),
            }
        )

    total_count = len(supply_entries)
    avg_coverage = int(round(coverage_total / total_count)) if total_count else 0
    top_capabilities = [
        {"name": name, "count": count}
        for name, count in capability_counts.most_common(6)
    ]

    return {
        "total_count": total_count,
        "avg_coverage": avg_coverage,
        "facilities": facilities,
        "top_capabilities": top_capabilities,
    }


def build_gap_analysis() -> Dict[str, Any]:
    virtue_rows = _load_virtue_rows()
    if virtue_rows:
        supply = build_supply_data()
        demand = build_demand_data()
        supply_by_region: Dict[str, int] = {}
        for facility in supply.get("facilities", []):
            region = facility.get("region", "Unknown")
            supply_by_region[region] = supply_by_region.get(region, 0) + 1

        demand_by_region: Dict[str, int] = {}
        for point in demand.get("points", []):
            region = point.get("region", "Unknown")
            demand_by_region[region] = demand_by_region.get(region, 0) + 1

        deserts = []
        total_population = 0
        gap_scores = []
        region_caps: Dict[str, Counter[str]] = {}
        for facility in supply.get("facilities", []):
            region = facility.get("region", "Unknown")
            region_caps.setdefault(region, Counter()).update(
                facility.get("capabilities", [])
            )

        global_caps = Counter()
        for counter in region_caps.values():
            global_caps.update(counter)
        top_global_caps = [cap for cap, _ in global_caps.most_common(8)]

        for idx, (region, demand_count) in enumerate(demand_by_region.items()):
            supply_count = supply_by_region.get(region, 0)
            gap_score = min(1.0, (demand_count / max(1, supply_count)) / 10)
            population = int(max(8000, demand_count * 1200))
            lat, lng = _region_coords(region)
            missing = [
                cap
                for cap in top_global_caps
                if cap not in (region_caps.get(region) or Counter())
            ][:4]
            nearest_km = int(25 + gap_score * 110)
            deserts.append(
                {
                    "id": f"g{idx + 1}",
                    "region_name": region,
                    "lat": lat,
                    "lng": lng,
                    "gap_score": round(gap_score, 3),
                    "population_affected": population,
                    "missing_capabilities": missing,
                    "nearest_facility_km": nearest_km,
                }
            )
            total_population += population
            gap_scores.append(gap_score)

        avg_gap_score = sum(gap_scores) / len(gap_scores) if gap_scores else 0.0
        return {
            "deserts": deserts,
            "total_population_underserved": total_population,
            "avg_gap_score": avg_gap_score,
        }

    gap_entries = load_json("gap_analysis.json")
    deserts = []
    total_population = 0
    gap_scores = []

    for idx, entry in enumerate(gap_entries):
        gap_score = float(entry.get("gap_score", 0.0))
        demand_count = int(entry.get("demand_count", 0))
        population = int(max(10000, (demand_count + 1) * 60000 * max(gap_score, 0.2)))
        nearest_km = int(20 + gap_score * 120)

        deserts.append(
            {
                "id": f"g{idx + 1}",
                "region_name": entry.get("region_name", "Unknown"),
                "lat": float(entry.get("lat", 0.0)),
                "lng": float(entry.get("lng", 0.0)),
                "gap_score": gap_score,
                "population_affected": population,
                "missing_capabilities": [
                    format_capability(cap)
                    for cap in entry.get("missing_capabilities", [])
                ],
                "nearest_facility_km": nearest_km,
            }
        )
        total_population += population
        gap_scores.append(gap_score)

    avg_gap_score = sum(gap_scores) / len(gap_scores) if gap_scores else 0.0

    return {
        "deserts": deserts,
        "total_population_underserved": total_population,
        "avg_gap_score": avg_gap_score,
    }


def build_map_data() -> Dict[str, Any]:
    virtue_rows = _load_virtue_rows()
    if virtue_rows:
        demand = build_demand_data()
        supply = build_supply_data()
        demand_points = []
        for idx, point in enumerate(demand.get("points", [])):
            lat, lng = _jitter_coords(point["lat"], point["lng"], idx + 3)
            demand_points.append(
                {
                    "lat": lat + 0.01,
                    "lng": lng + 0.015,
                    "intensity": point["intensity"],
                }
            )
        supply_points = []
        for idx, facility in enumerate(supply.get("facilities", [])):
            lat, lng = _jitter_coords(facility["lat"], facility["lng"], idx + 7)
            supply_points.append(
                {
                    "lat": lat - 0.01,
                    "lng": lng - 0.015,
                    "coverage": facility["coverage"],
                }
            )
        return {"demand_points": demand_points, "supply_points": supply_points}

    map_entries = load_json("map_data.json")
    demand_points = []
    supply_points = []

    for entry in map_entries:
        label = entry.get("label", "")
        if label.startswith("Demand:"):
            demand_points.append(
                {
                    "lat": float(entry.get("lat", 0.0)),
                    "lng": float(entry.get("lng", 0.0)),
                    "intensity": float(entry.get("intensity", 0.0)),
                }
            )
        elif label.startswith("Supply:"):
            supply_points.append(
                {
                    "lat": float(entry.get("lat", 0.0)),
                    "lng": float(entry.get("lng", 0.0)),
                    "coverage": int(round(float(entry.get("intensity", 0.0)) * 100)),
                }
            )

    return {"demand_points": demand_points, "supply_points": supply_points}


def build_recommendations() -> Dict[str, Any]:
    virtue_rows = _load_virtue_rows()
    if virtue_rows:
        gap = build_gap_analysis()
        formatted = []
        for idx, desert in enumerate(gap.get("deserts", [])):
            missing_caps = desert.get("missing_capabilities", []) or ["Capacity upgrades"]
            gap_score = desert.get("gap_score", 0)
            population = desert.get('population_affected', 0)
            
            # Create varied actions based on gap score and missing capabilities
            if gap_score > 0.7:
                action_templates = ["Urgent expansion of {cap}", "Critical upgrade: {cap} services", "Immediate {cap} deployment"]
            elif gap_score > 0.5:
                action_templates = ["Priority upgrade for {cap}", "Scale {cap} capacity", "Strengthen {cap} coverage"]
            else:
                action_templates = ["Expand {cap} coverage", "Enhance {cap} services", "Improve {cap} access"]
            
            cap_name = missing_caps[0] if missing_caps else "healthcare capacity"
            action = action_templates[idx % len(action_templates)].format(cap=cap_name)
            print(f"DEBUG: Building rec {idx}: region={desert.get('region_name')}, action={action}")
            
            # Vary the impact descriptions
            reduction_k = max(5, int(population / 1000))
            coverage_gain = int(round(10 + gap_score * 30))
            impact = f"Reduce underserved by ~{reduction_k}K (+{coverage_gain}% coverage)"
            
            # Vary costs based on gap score and population
            base_cost = 120 + gap_score * 600 + (population / 50000) * 100
            
            formatted.append(
                {
                    "id": f"r{idx + 1}",
                    "region": desert.get("region_name", "Unknown"),
                    "action": action,
                    "capability_needed": ", ".join(missing_caps),
                    "estimated_impact": impact,
                    "roi": f"${base_cost:.0f}K",
                    "priority": "critical" if gap_score > 0.75 else ("high" if gap_score > 0.6 else ("medium" if gap_score > 0.4 else "low")),
                    "lives_saved_per_year": max(8, min(80, int(len(missing_caps) * 12 * (0.5 + gap_score)))),
                }
            )
        return {"recommendations": formatted}

    recommendations = load_json("planner_recommendations.json")
    formatted = []

    for idx, rec in enumerate(recommendations):
        missing_caps = [
            format_capability(cap) for cap in rec.get("missing_capabilities", [])
        ]
        cost = int(rec.get("estimated_cost_usd", 0))
        lives_saved = max(5, min(60, 8 * max(len(missing_caps), 1)))

        formatted.append(
            {
                "id": f"r{idx + 1}",
                "region": rec.get("region_name", "Unknown"),
                "action": rec.get("recommended_actions", ["Capacity upgrade"])[0],
                "capability_needed": ", ".join(missing_caps) or "Capacity upgrades",
                "estimated_impact": rec.get("expected_impact", ""),
                "roi": f"${cost / 1000:.0f}K",
                "priority": rec.get("priority", "medium"),
                "lives_saved_per_year": lives_saved,
            }
        )

    return {"recommendations": formatted}


def build_planner_engine_data(trace_id: str) -> Dict[str, Any]:
    demand = build_demand_data()
    supply = build_supply_data()
    gap = build_gap_analysis()
    recommendations = build_recommendations().get("recommendations", [])
    hotspots = [
        {
            "region": item.get("region_name"),
            "gap_score": item.get("gap_score"),
            "population_affected": item.get("population_affected"),
            "lat": item.get("lat"),
            "lng": item.get("lng"),
        }
        for item in gap.get("deserts", [])
    ]
    baseline_kpis = {
        "demand_total": demand.get("total_count", 0),
        "avg_coverage": supply.get("avg_coverage", 0),
        "total_population_underserved": gap.get("total_population_underserved", 0),
        "avg_gap_score": gap.get("avg_gap_score", 0),
    }
    payload = {
        "region": hotspots[0]["region"] if hotspots else "Region",
        "demand": demand,
        "supply": supply,
        "gap": gap,
        "hotspots": hotspots,
        "recommendations": recommendations,
        "baseline_kpis": baseline_kpis,
    }
    if _demo_mode_enabled():
        return payload
    build_planner_response = _lazy_import(
        "src.intelligence.planner_engine", "build_planner_response"
    )
    if build_planner_response is None:
        return payload
    return build_planner_response(payload, trace_id=trace_id)


def _use_legacy_output() -> bool:
    flag = request.args.get("legacy")
    if flag is not None:
        return str(flag).lower() != "false"
    return os.getenv("OUTPUT_LEGACY_STRINGS", "true").lower() != "false"


def _apply_legacy_flag(payload: Dict, legacy: bool) -> Dict:
    payload["legacy"] = legacy
    return payload


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "HealthGrid AI"})


@app.route("/parse/demand", methods=["POST"])
def parse_demand():
    """Parse patient report, return demand requirements."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    trace_id = payload.get("trace_id") or _create_trace_id()
    use_fallback = (
        request.args.get("fallback") == "true"
        or os.getenv("LLM_DISABLED", "false").lower() == "true"
        or _demo_mode_enabled()
    )
    parse_demand_fallback = _lazy_import(
        "src.demand.fallback_parse", "parse_demand_fallback"
    )
    extract_demand_from_text = (
        None
        if use_fallback
        else _lazy_import("src.demand.profile_extractor", "extract_demand_from_text")
    )
    result = None
    if extract_demand_from_text is not None:
        try:
            result = extract_demand_from_text(text, trace_id=trace_id)
        except Exception:
            result = None
    if result is None and parse_demand_fallback is not None:
        result = parse_demand_fallback(text)
    if result is None:
        payload = {
            "profile": {
                "patient_id": "demo-patient",
                "diagnosis": "Unknown",
                "stage": "",
                "biomarkers": [],
                "location": "Unknown",
                "urgency_score": 5,
            },
            "required_capabilities": [],
            "travel_radius_km": 50,
            "evidence": [],
        }
        return jsonify(payload)
    if hasattr(result, "model_dump"):
        return jsonify(result.model_dump())
    return jsonify(result)


@app.route("/parse/supply", methods=["POST"])
def parse_supply():
    """Parse facility doc, return capabilities."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    source_doc_id = payload.get("source_doc_id") or payload.get("filename") or "facility_document"
    trace_id = payload.get("trace_id") or _create_trace_id()
    output_legacy = _use_legacy_output()
    _trace_event(
        trace_id,
        "ingest",
        inputs_ref={"source_doc_id": source_doc_id, "text_length": len(text)},
    )
    _trace_event(
        trace_id,
        "chunking",
        outputs_ref={"chunk_count": 1},
        notes="Single text chunk input",
    )
    if _demo_mode_enabled():
        return jsonify(
            _apply_legacy_flag(
                {
                    "supply": {
                        "facility_id": source_doc_id,
                        "capabilities": [],
                        "equipment": [],
                        "specialists": [],
                        "evidence_index": {},
                    },
                    "citations": [],
                    "trace_id": trace_id,
                    "demo": True,
                },
                output_legacy,
            )
        )
    use_fallback = request.args.get("fallback") == "true" or os.getenv("LLM_DISABLED", "false").lower() == "true"
    parse_supply_fallback = _lazy_import(
        "src.supply.fallback_parse", "parse_supply_fallback"
    )
    parse_facility_document = (
        None
        if use_fallback
        else _lazy_import("src.supply.facility_parser", "parse_facility_document")
    )
    result = None
    if parse_facility_document is not None:
        try:
            result = parse_facility_document(
                text, source_doc_id=source_doc_id, trace_id=trace_id
            )
        except Exception:
            result = None
    if result is None and parse_supply_fallback is not None:
        result = parse_supply_fallback(text, source_doc_id=source_doc_id)
    if result is None:
        return jsonify({"detail": "Supply parsing failed"}), 500
    chunks = [
        {
            "chunk_id": "chunk_0",
            "source_doc_id": source_doc_id,
            "text_snippet": text[:200],
            "locator": {"chunk_id": "chunk_0"},
        }
    ]
    build_evidence_index = _lazy_import(
        "src.supply.evidence_index", "build_evidence_index"
    )
    evidence_index = (
        build_evidence_index(chunks, result.citations)
        if build_evidence_index is not None
        else {}
    )
    _trace_event(
        trace_id,
        "llm_extract_supply",
        outputs_ref={
            "num_capabilities": len(result.capabilities),
            "num_equipment": len(result.equipment),
            "num_specialists": len(result.specialists),
        },
    )
    _trace_event(
        trace_id,
        "attach_citations",
        outputs_ref={"num_citations": len(result.citations)},
        citation_ids=[item.citation_id for item in result.citations],
    )
    unmatched = [
        entry
        for entry in result.capabilities + result.equipment + result.specialists
        if getattr(entry, "capability_code", None) is None
    ]
    _trace_event(
        trace_id,
        "normalize_ontology",
        outputs_ref={
            "matched_codes": len(result.canonical_capabilities or []),
            "unmatched_entries": len(unmatched),
        },
    )
    if payload.get("validate", True):
        validate_supply = _lazy_import(
            "src.validation.anomaly_agent", "validate_supply"
        )
        validation = (
            validate_supply(result.model_dump(), trace_id=trace_id)
            if validate_supply is not None
            else {"verdict": "demo", "issue_count_by_severity": {}}
        )
        if hasattr(validation, "verdict"):
            _trace_event(
                trace_id,
                "validate_supply",
                outputs_ref={
                    "verdict": validation.verdict,
                    "issues": validation.issue_count_by_severity,
                },
            )
        supply_payload = result.model_dump()
        supply_payload["evidence_index"] = evidence_index
        if output_legacy:
            supply_payload["capabilities_legacy"] = result.capabilities_legacy
            supply_payload["equipment_legacy"] = result.equipment_legacy
            supply_payload["specialists_legacy"] = result.specialists_legacy
        return jsonify(
            _apply_legacy_flag(
                {
                    "supply": supply_payload,
                    "citations": [item.model_dump() for item in result.citations],
                    "trace_id": trace_id,
                    "validation": validation.model_dump()
                    if hasattr(validation, "model_dump")
                    else validation,
                },
                output_legacy,
            )
        )
    supply_payload = result.model_dump()
    supply_payload["evidence_index"] = evidence_index
    if output_legacy:
        supply_payload["capabilities_legacy"] = result.capabilities_legacy
        supply_payload["equipment_legacy"] = result.equipment_legacy
        supply_payload["specialists_legacy"] = result.specialists_legacy
    return jsonify(
        _apply_legacy_flag(
            {
                "supply": supply_payload,
                "citations": [item.model_dump() for item in result.citations],
                "trace_id": trace_id,
            },
            output_legacy,
        )
    )


@app.route("/validate/supply", methods=["POST"])
def validate_supply_route():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    supply = payload.get("supply") or {}
    facility_schema = payload.get("facility_schema")
    constraints = payload.get("constraints")
    validate_supply = _lazy_import("src.validation.anomaly_agent", "validate_supply")
    validation = (
        validate_supply(supply, facility_schema, constraints, trace_id=trace_id)
        if validate_supply is not None
        else {"verdict": "demo", "issue_count_by_severity": {}}
    )
    if hasattr(validation, "verdict"):
        _trace_event(
            trace_id,
            "validate_supply",
            outputs_ref={
                "verdict": validation.verdict,
                "issues": validation.issue_count_by_severity,
            },
        )
    payload = (
        validation.model_dump() if hasattr(validation, "model_dump") else validation
    )
    return jsonify(_apply_legacy_flag(payload, _use_legacy_output()))


@app.route("/intelligence/gaps", methods=["POST"])
def intelligence_gaps():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    demand = payload.get("demand") or {}
    supply = payload.get("supply") or []
    params = payload.get("params") or {}
    detect_gaps = _lazy_import("src.intelligence.gap_detection", "detect_gaps")
    if detect_gaps is None or _demo_mode_enabled():
        result = {"gaps": [], "map": {"facility_points": []}, "demo": True}
    else:
        result = detect_gaps(demand, supply, params, trace_id=trace_id)
    _trace_event(
        trace_id,
        "gap_detection",
        inputs_ref={"params": params},
        outputs_ref={
            "gap_count": len(result.get("gaps", [])),
            "facility_ids": [
                item.get("facility_id")
                for item in result.get("map", {}).get("facility_points", [])
            ],
        },
    )
    result["trace_id"] = trace_id
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/planner/plan", methods=["POST"])
def planner_plan():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    plan_actions = _lazy_import("src.intelligence.planner", "plan_actions")
    if plan_actions is None or _demo_mode_enabled():
        result = {"immediate": [], "near_term": [], "invest": [], "demo": True}
    else:
        result = plan_actions(payload, trace_id=trace_id)
    _trace_event(
        trace_id,
        "planner",
        outputs_ref={
            "immediate": len(result.get("immediate", [])),
            "near_term": len(result.get("near_term", [])),
            "invest": len(result.get("invest", [])),
        },
    )
    _log_trace(
        trace_id,
        outputs={"planner": result},
        params={"region": (payload.get("demand") or {}).get("location")},
    )
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/planner/query", methods=["POST"])
def planner_query():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    plan_from_query = _lazy_import("src.intelligence.planner", "plan_from_query")
    if plan_from_query is None or _demo_mode_enabled():
        result = {"plan": {"steps": []}, "next_actions": [], "demo": True}
    else:
        result = plan_from_query(payload, trace_id=trace_id)
    _trace_event(
        trace_id,
        "planner_query",
        outputs_ref={
            "steps": len((result.get("plan") or {}).get("steps", [])),
            "actions": len(result.get("next_actions") or []),
        },
    )
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/facility/answer", methods=["POST"])
def facility_answer():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    answer_facility = _lazy_import("src.intelligence.facility_answer", "answer_facility")
    if answer_facility is None or _demo_mode_enabled():
        result = {"ok": True, "demo": True}
    else:
        result = answer_facility(payload, trace_id=trace_id)
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/analytics/deserts", methods=["POST"])
def analytics_deserts():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    analyze_deserts = _lazy_import("src.analytics.deserts", "analyze_deserts")
    if analyze_deserts is None or _demo_mode_enabled():
        result = {"top_deserts": [], "summary": {}, "demo": True}
    else:
        result = analyze_deserts(payload, trace_id=trace_id)
    _trace_event(
        trace_id,
        "desert_analytics",
        outputs_ref={
            "deserts_found": len(result.get("top_deserts", [])),
            "total_demands": (result.get("summary") or {}).get("total_demands"),
        },
    )
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/analytics/deserts/score", methods=["POST"])
def analytics_desert_score():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    score_deserts = _lazy_import("src.analytics.desert_scoring", "score_deserts")
    if score_deserts is None or _demo_mode_enabled():
        result = {"scores": [], "demo": True}
    else:
        result = score_deserts(payload, trace_id=trace_id)
    _log_trace(
        trace_id,
        outputs={"desert_scores": result.get("scores", [])},
        params={
            "capability_target": payload.get("capability_target"),
            "region": payload.get("region"),
        },
    )
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/trace/<trace_id>/summary", methods=["GET"])
def get_trace_summary(trace_id: str):
    events = _read_trace(trace_id)
    llm_steps = _get_trace_steps(trace_id)
    step_counts: Dict[str, int] = {}
    for event in events:
        step = event.get("step_name")
        if not step:
            continue
        step_counts[step] = step_counts.get(step, 0) + 1
    summary = {
        "trace_id": trace_id,
        "step_counts": step_counts,
        "event_count": len(events),
        "llm_step_count": len(llm_steps),
    }
    return jsonify(summary)


@app.route("/trace/<trace_id>", methods=["GET"])
def get_trace(trace_id: str):
    return jsonify(
        {
            "trace_id": trace_id,
            "events": _read_trace(trace_id),
            "llm_steps": _get_trace_steps(trace_id),
        }
    )


@app.route("/data/demand", methods=["GET"])
def data_demand():
    return jsonify(build_demand_data())


@app.route("/data/supply", methods=["GET"])
def data_supply():
    return jsonify(build_supply_data())


@app.route("/data/gap", methods=["GET"])
def data_gap():
    return jsonify(build_gap_analysis())


@app.route("/data/map", methods=["GET"])
def data_map():
    return jsonify(build_map_data())


@app.route("/data/recommendations", methods=["GET"])
def data_recommendations():
    return jsonify(build_recommendations())


@app.route("/data/planner_engine", methods=["GET"])
def data_planner_engine():
    trace_id = _create_trace_id()
    return jsonify(build_planner_engine_data(trace_id))


@app.route("/planner/engine", methods=["POST"])
def planner_engine():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or _create_trace_id()
    build_planner_response = _lazy_import(
        "src.intelligence.planner_engine", "build_planner_response"
    )
    if build_planner_response is None or _demo_mode_enabled():
        return jsonify({"trace_id": trace_id, "demo": True, "payload": payload})
    result = build_planner_response(payload, trace_id=trace_id)
    return jsonify(result)


@app.route("/upload/dataset", methods=["POST"])
def upload_dataset():
    """Upload a custom CSV dataset to replace the default one"""
    if "file" not in request.files:
        return jsonify({"detail": "No file provided"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"detail": "No file selected"}), 400

    try:
        uploads_dir = PROJECT_ROOT / "data" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename).name or f"upload_{uuid.uuid4().hex}.csv"
        target_path = uploads_dir / safe_name
        file.save(str(target_path))
        size_bytes = target_path.stat().st_size if target_path.exists() else 0
        return (
            jsonify(
                {
                    "ok": True,
                    "demo": True,
                    "message": "uploaded (processing skipped in demo mode)",
                    "filename": safe_name,
                    "size_bytes": size_bytes,
                }
            ),
            202,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "ok": True,
                    "demo": True,
                    "message": f"uploaded (processing skipped in demo mode): {str(e)}",
                    "filename": file.filename,
                    "size_bytes": 0,
                }
            ),
            202,
        )


def _is_api_path(path: str) -> bool:
    return path.startswith("/api")


class _DummyFastAPI:
    def mount(self, *args: Any, **kwargs: Any) -> None:
        return

    def exception_handler(self, *args: Any, **kwargs: Any):
        def decorator(fn):
            return fn

        return decorator


fastapi_app = FastAPI() if FastAPI is not None else _DummyFastAPI()
fastapi_app.mount("/api", WSGIMiddleware(app))
fastapi_app.mount(
    "/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static"
)


@fastapi_app.exception_handler(StarletteHTTPException)
async def spa_fallback(
    request: FastAPIRequest, exc: StarletteHTTPException
) -> JSONResponse | FileResponse:
    if exc.status_code == 404 and not _is_api_path(request.url.path):
        if INDEX_FILE.exists():
            return FileResponse(INDEX_FILE)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


app = fastapi_app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
