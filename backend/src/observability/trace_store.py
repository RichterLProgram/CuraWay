from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_TRACE_STORE: Dict[str, List[Dict[str, Any]]] = {}


def record_llm_call(
    trace_id: str,
    step_id: str,
    provider: str,
    model: str,
    prompt: str,
    response_text: str,
    usage: Dict[str, Any],
    latency_ms: int,
    input_refs: Optional[Dict[str, Any]] = None,
    output_claims: Optional[Dict[str, Any]] = None,
) -> None:
    step = {
        "step_id": step_id,
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "response_text": response_text,
        "usage": usage,
        "latency_ms": latency_ms,
        "input_refs": input_refs or {},
        "output_claims": output_claims or {},
    }
    with _LOCK:
        _TRACE_STORE.setdefault(trace_id, []).append(step)


def get_trace_steps(trace_id: str) -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_TRACE_STORE.get(trace_id, []))


def export_trace(trace_id: str, path: str) -> None:
    steps = get_trace_steps(trace_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"trace_id": trace_id, "steps": steps}, handle, ensure_ascii=False, indent=2)
