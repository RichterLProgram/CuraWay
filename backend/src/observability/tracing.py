from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def create_trace_id() -> str:
    return str(uuid.uuid4())


def trace_event(
    trace_id: str,
    step_name: str,
    inputs_ref: Optional[Dict[str, Any]] = None,
    outputs_ref: Optional[Dict[str, Any]] = None,
    citation_ids: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> None:
    event = {
        "trace_id": trace_id,
        "step_name": step_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs_ref": inputs_ref or {},
        "outputs_ref": outputs_ref or {},
        "citation_ids": citation_ids or [],
        "notes": notes or "",
    }

    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "logs",
        "traces",
    )
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, f"{trace_id}.jsonl")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    exporters = os.getenv("TRACE_EXPORT", "jsonl").lower().split(",")
    if "mlflow" in exporters:
        _export_mlflow(trace_id, event)
    if "otel" in exporters or "opentelemetry" in exporters:
        _export_otel(trace_id, event)


def read_trace(trace_id: str) -> List[Dict[str, Any]]:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "logs",
        "traces",
        f"{trace_id}.jsonl",
    )
    if not os.path.exists(path):
        return []
    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _export_mlflow(trace_id: str, event: Dict[str, Any]) -> None:
    try:
        import mlflow  # type: ignore
    except Exception:
        return
    try:
        mlflow.set_experiment("trace-events")
        with mlflow.start_run(run_name=trace_id):
            mlflow.log_dict(event, f"trace_{trace_id}.json")
    except Exception:
        return


def _export_otel(trace_id: str, event: Dict[str, Any]) -> None:
    try:
        from opentelemetry import trace  # type: ignore
    except Exception:
        return
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(event.get("step_name", "trace_event")) as span:
            span.set_attribute("trace_id", trace_id)
            for key, value in (event.get("outputs_ref") or {}).items():
                span.set_attribute(f"outputs.{key}", str(value))
    except Exception:
        return
