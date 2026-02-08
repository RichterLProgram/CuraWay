from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, request
from flask_cors import CORS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.demand.fallback_parse import parse_demand_fallback
from src.demand.profile_extractor import extract_demand_from_text
from src.intelligence.facility_answer import answer_facility
from src.intelligence.gap_detection import detect_gaps
from src.intelligence.planner import plan_actions, plan_from_query
from src.analytics.deserts import analyze_deserts
from src.analytics.desert_scoring import score_deserts
from src.observability.trace_store import get_trace_steps
from src.observability.mlflow_logger import log_trace
from src.observability.tracing import create_trace_id, read_trace, trace_event
from src.supply.facility_parser import parse_facility_document
from src.supply.fallback_parse import parse_supply_fallback
from src.supply.evidence_index import build_evidence_index
from src.validation.anomaly_agent import validate_supply


app = Flask(__name__)
CORS(app)

DATA_DIR = PROJECT_ROOT / "output" / "data"


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


def build_demand_data() -> Dict[str, Any]:
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
    trace_id = payload.get("trace_id") or create_trace_id()
    use_fallback = request.args.get("fallback") == "true" or os.getenv("LLM_DISABLED", "false").lower() == "true"
    if use_fallback:
        result = parse_demand_fallback(text)
    else:
        try:
            result = extract_demand_from_text(text, trace_id=trace_id)
        except Exception:
            result = parse_demand_fallback(text)
    return jsonify(result.model_dump())


@app.route("/parse/supply", methods=["POST"])
def parse_supply():
    """Parse facility doc, return capabilities."""
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    source_doc_id = payload.get("source_doc_id") or payload.get("filename") or "facility_document"
    trace_id = payload.get("trace_id") or create_trace_id()
    output_legacy = _use_legacy_output()
    trace_event(
        trace_id,
        "ingest",
        inputs_ref={"source_doc_id": source_doc_id, "text_length": len(text)},
    )
    trace_event(
        trace_id,
        "chunking",
        outputs_ref={"chunk_count": 1},
        notes="Single text chunk input",
    )
    use_fallback = request.args.get("fallback") == "true" or os.getenv("LLM_DISABLED", "false").lower() == "true"
    if use_fallback:
        result = parse_supply_fallback(text, source_doc_id=source_doc_id)
    else:
        try:
            result = parse_facility_document(
                text, source_doc_id=source_doc_id, trace_id=trace_id
            )
        except Exception:
            result = parse_supply_fallback(text, source_doc_id=source_doc_id)
    chunks = [
        {
            "chunk_id": "chunk_0",
            "source_doc_id": source_doc_id,
            "text_snippet": text[:200],
            "locator": {"chunk_id": "chunk_0"},
        }
    ]
    evidence_index = build_evidence_index(chunks, result.citations)
    trace_event(
        trace_id,
        "llm_extract_supply",
        outputs_ref={
            "num_capabilities": len(result.capabilities),
            "num_equipment": len(result.equipment),
            "num_specialists": len(result.specialists),
        },
    )
    trace_event(
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
    trace_event(
        trace_id,
        "normalize_ontology",
        outputs_ref={
            "matched_codes": len(result.canonical_capabilities or []),
            "unmatched_entries": len(unmatched),
        },
    )
    if payload.get("validate", True):
        validation = validate_supply(result.model_dump(), trace_id=trace_id)
        trace_event(
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
                    "validation": validation.model_dump(),
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
    trace_id = payload.get("trace_id") or create_trace_id()
    supply = payload.get("supply") or {}
    facility_schema = payload.get("facility_schema")
    constraints = payload.get("constraints")
    validation = validate_supply(supply, facility_schema, constraints, trace_id=trace_id)
    trace_event(
        trace_id,
        "validate_supply",
        outputs_ref={
            "verdict": validation.verdict,
            "issues": validation.issue_count_by_severity,
        },
    )
    return jsonify(_apply_legacy_flag(validation.model_dump(), _use_legacy_output()))


@app.route("/intelligence/gaps", methods=["POST"])
def intelligence_gaps():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or create_trace_id()
    demand = payload.get("demand") or {}
    supply = payload.get("supply") or []
    params = payload.get("params") or {}
    result = detect_gaps(demand, supply, params, trace_id=trace_id)
    trace_event(
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
    trace_id = payload.get("trace_id") or create_trace_id()
    result = plan_actions(payload, trace_id=trace_id)
    trace_event(
        trace_id,
        "planner",
        outputs_ref={
            "immediate": len(result.get("immediate", [])),
            "near_term": len(result.get("near_term", [])),
            "invest": len(result.get("invest", [])),
        },
    )
    log_trace(
        trace_id,
        outputs={"planner": result},
        params={"region": (payload.get("demand") or {}).get("location")},
    )
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/planner/query", methods=["POST"])
def planner_query():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or create_trace_id()
    result = plan_from_query(payload, trace_id=trace_id)
    trace_event(
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
    trace_id = payload.get("trace_id") or create_trace_id()
    result = answer_facility(payload, trace_id=trace_id)
    return jsonify(_apply_legacy_flag(result, _use_legacy_output()))


@app.route("/analytics/deserts", methods=["POST"])
def analytics_deserts():
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id") or create_trace_id()
    result = analyze_deserts(payload, trace_id=trace_id)
    trace_event(
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
    trace_id = payload.get("trace_id") or create_trace_id()
    result = score_deserts(payload, trace_id=trace_id)
    log_trace(
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
    events = read_trace(trace_id)
    llm_steps = get_trace_steps(trace_id)
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
            "events": read_trace(trace_id),
            "llm_steps": get_trace_steps(trace_id),
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
