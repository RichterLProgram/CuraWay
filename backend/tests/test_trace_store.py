import os

from src.observability.trace_store import get_trace_steps
from src.supply.facility_parser import parse_facility_document


def test_llm_trace_steps_created():
    os.environ["LLM_DISABLED"] = "true"
    trace_id = "trace-test-1"
    text = "Facility offers CT scan and oncology services."
    parse_facility_document(text, source_doc_id="doc-1", trace_id=trace_id)
    steps = get_trace_steps(trace_id)
    assert steps
    assert any(step.get("step_id") == "facility_extract" for step in steps)
