from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from src.observability.trace_store import export_trace, get_trace_steps

logger = logging.getLogger(__name__)


def log_trace(
    trace_id: str,
    outputs: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> bool:
    if not _enabled():
        return False
    mlflow = _load_mlflow()
    if mlflow is None:
        return False

    outputs = outputs or {}
    params = params or {}
    try:
        experiment = os.getenv("MLFLOW_EXPERIMENT", "CancerCompass")
        mlflow.set_experiment(experiment)
        with mlflow.start_run(run_name=trace_id):
            log_params = _build_params(trace_id, params)
            log_metrics = _build_metrics(trace_id, outputs)
            if log_params:
                mlflow.log_params(log_params)
            if log_metrics:
                mlflow.log_metrics(log_metrics)
            _log_artifacts(mlflow, trace_id, outputs)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("MLflow logging failed: %s", exc)
        return False


def _enabled() -> bool:
    return os.getenv("MLFLOW_ENABLED", "false").lower() == "true"


def _load_mlflow():
    try:
        import mlflow  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        logger.warning("MLflow is not installed; skipping MLflow export.")
        return None
    return mlflow


def _build_params(trace_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    model = params.get("model") or _first_step_model(trace_id)
    temperature = params.get("temperature")
    if temperature is None:
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    capability_target = params.get("capability_target")
    region = params.get("region")
    if isinstance(region, dict):
        region = json.dumps(region, ensure_ascii=False)
    return {
        "model": model,
        "temperature": temperature,
        "capability_target": capability_target,
        "region": region,
    }


def _build_metrics(trace_id: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
    steps = get_trace_steps(trace_id)
    latency_ms = sum(int(step.get("latency_ms", 0)) for step in steps)
    token_in, token_out = _extract_tokens(steps)
    num_claims = sum(len(step.get("output_claims", {}) or {}) for step in steps)
    num_flags = len(outputs.get("risk_flags") or [])
    if "desert_scores" in outputs:
        num_flags = sum(
            len(item.get("risk_flags") or [])
            for item in outputs.get("desert_scores") or []
        )
    metrics = {
        "latency_ms": latency_ms,
        "token_in": token_in,
        "token_out": token_out,
        "num_claims": num_claims,
        "num_flags": num_flags,
    }
    return {key: value for key, value in metrics.items() if value is not None}


def _extract_tokens(steps: list[dict]) -> Tuple[int, int]:
    token_in = 0
    token_out = 0
    for step in steps:
        usage = step.get("usage") or {}
        token_in += int(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("tokens_in")
            or 0
        )
        token_out += int(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("tokens_out")
            or 0
        )
    return token_in, token_out


def _first_step_model(trace_id: str) -> Optional[str]:
    steps = get_trace_steps(trace_id)
    if not steps:
        return None
    return steps[0].get("model")


def _log_artifacts(mlflow: Any, trace_id: str, outputs: Dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = os.path.join(tmpdir, f"trace_{trace_id}.json")
        export_trace(trace_id, trace_path)
        mlflow.log_artifact(trace_path, artifact_path="traces")

        output_path = os.path.join(tmpdir, f"desert_scores_{trace_id}.json")
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(outputs, handle, ensure_ascii=False, indent=2)
        mlflow.log_artifact(output_path, artifact_path="outputs")
