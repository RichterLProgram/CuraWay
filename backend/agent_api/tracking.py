from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.observability.mlflow_logger import log_trace
from src.observability.tracing import trace_event


def trace_agent_start(trace_id: str, inputs: Dict[str, Any]) -> None:
    trace_event(trace_id, "agent_start", inputs_ref=inputs)


def trace_agent_step(
    trace_id: str,
    step_name: str,
    inputs: Optional[Dict[str, Any]] = None,
    outputs: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
) -> None:
    trace_event(
        trace_id,
        step_name,
        inputs_ref=inputs or {},
        outputs_ref=outputs or {},
        notes=notes,
    )


def trace_agent_end(
    trace_id: str,
    outputs: Dict[str, Any],
    params: Dict[str, Any],
) -> bool:
    return log_trace(trace_id, outputs=outputs, params=params)


class Stopwatch:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)
