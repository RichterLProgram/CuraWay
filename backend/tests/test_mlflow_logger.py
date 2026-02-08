import os
import sys

from src.observability import mlflow_logger
from src.observability.trace_store import record_llm_call


class DummyMlflow:
    def __init__(self):
        self.params = None
        self.metrics = None
        self.artifacts = []
        self.experiment = None

    def set_experiment(self, name):
        self.experiment = name

    def start_run(self, run_name=None):
        self.run_name = run_name
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def log_params(self, params):
        self.params = params

    def log_metrics(self, metrics):
        self.metrics = metrics

    def log_artifact(self, path, artifact_path=None):
        self.artifacts.append((path, artifact_path))


def test_mlflow_logger_calls(monkeypatch):
    os.environ["MLFLOW_ENABLED"] = "true"
    dummy = DummyMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", dummy)

    trace_id = "trace-mlflow-1"
    record_llm_call(
        trace_id=trace_id,
        step_id="step-1",
        provider="mock",
        model="mock-model",
        prompt="prompt",
        response_text="response",
        usage={"prompt_tokens": 10, "completion_tokens": 5},
        latency_ms=12,
        input_refs={},
        output_claims={"claim": "value"},
    )

    ok = mlflow_logger.log_trace(
        trace_id,
        outputs={"desert_scores": []},
        params={"capability_target": "IMAGING_CT", "region": "Region"},
    )
    assert ok is True
    assert dummy.params["capability_target"] == "IMAGING_CT"
    assert "latency_ms" in dummy.metrics
    assert dummy.artifacts
