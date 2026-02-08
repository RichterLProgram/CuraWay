from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from flask import Flask, jsonify, request
from flask_cors import CORS
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.wsgi import WSGIMiddleware

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


STATIC_DIR = Path(__file__).resolve().parents[2] / "backend" / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app = Flask(__name__)
CORS(app)
print(f"Starting app; serving static at {STATIC_DIR}; health at /api/health")


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


def _static_debug_payload() -> Dict[str, str]:
    return {
        "detail": "Frontend not built",
        "expected_static_dir": str(STATIC_DIR),
        "expected_index": str(INDEX_FILE),
    }


fastapi_app = FastAPI()


@fastapi_app.get("/api/health")
async def api_health() -> Dict[str, object]:
    return {"status": "ok", "ok": True}


@fastapi_app.get("/api")
async def api_root() -> Dict[str, object]:
    return {"status": "ok", "ok": True}


@fastapi_app.get("/api/ping")
async def api_ping() -> Dict[str, object]:
    return {"status": "ok", "ok": True}


fastapi_app.mount("/api", WSGIMiddleware(app))


@fastapi_app.get("/", response_model=None)
async def root():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return JSONResponse(_static_debug_payload(), status_code=200)


if STATIC_DIR.exists():
    fastapi_app.mount(
        "/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static"
    )


@fastapi_app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api"):
        if INDEX_FILE.exists():
            return FileResponse(INDEX_FILE)
        return JSONResponse(_static_debug_payload(), status_code=200)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


app = fastapi_app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
