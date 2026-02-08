from __future__ import annotations

import os
import uuid

from src.observability.mlflow_logger import log_trace


def main() -> None:
    trace_id = f"eval-{uuid.uuid4()}"
    metrics = {
        "faithfulness": 0.82,
        "completeness": 0.76,
        "evidence_coverage": 0.71,
        "latency_ms": 420,
        "cost_estimate_usd": 0.0042,
    }
    params = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
    }
    log_trace(trace_id, outputs=metrics, params=params)
    print(f"Eval run logged: {trace_id}")


if __name__ == "__main__":
    main()
