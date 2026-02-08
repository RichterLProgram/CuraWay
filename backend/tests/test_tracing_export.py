import os

from src.observability.tracing import create_trace_id, read_trace, trace_event


def test_trace_jsonl_written(tmp_path, monkeypatch):
    trace_id = create_trace_id()
    monkeypatch.setenv("TRACE_EXPORT", "jsonl")
    trace_event(trace_id, "unit_test", outputs_ref={"ok": True})
    events = read_trace(trace_id)
    assert any(event.get("step_name") == "unit_test" for event in events)


def test_trace_mlflow_missing_does_not_crash(monkeypatch):
    trace_id = create_trace_id()
    monkeypatch.setenv("TRACE_EXPORT", "mlflow")
    trace_event(trace_id, "unit_test_mlflow")
    events = read_trace(trace_id)
    assert events is not None
