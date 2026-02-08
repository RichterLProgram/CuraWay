from src.intelligence.facility_answer import answer_facility


def _facility(verdict="plausible"):
    return {
        "facility_id": "F-1",
        "canonical_capabilities": ["IMAGING_CT", "ONC_GENERAL"],
        "capabilities": [
            {"name": "CT scan", "capability_code": "IMAGING_CT", "citation_ids": ["c1"]},
            {"name": "Oncology", "capability_code": "ONC_GENERAL", "citation_ids": ["c2"]},
        ],
        "validation": {"verdict": verdict, "score": 0.9, "issues": []},
    }


def test_facility_answer_yes():
    payload = {
        "facility_id": "F-1",
        "required_capability_codes": ["IMAGING_CT", "ONC_GENERAL"],
        "facility": _facility(),
    }
    result = answer_facility(payload, trace_id="trace-1")
    assert result["answer"] == "yes"
    assert result["coverage_score"] == 1.0


def test_facility_answer_partial():
    payload = {
        "facility_id": "F-1",
        "required_capability_codes": ["IMAGING_CT", "ICU"],
        "facility": _facility(),
    }
    result = answer_facility(payload, trace_id="trace-2")
    assert result["answer"] == "partial"
    assert "ICU" in result["missing"]


def test_facility_answer_no():
    payload = {
        "facility_id": "F-1",
        "required_capability_codes": ["ICU"],
        "facility": _facility(),
    }
    result = answer_facility(payload, trace_id="trace-3")
    assert result["answer"] == "no"


def test_facility_answer_impossible_forces_no():
    payload = {
        "facility_id": "F-1",
        "required_capability_codes": ["IMAGING_CT"],
        "facility": _facility(verdict="impossible"),
    }
    result = answer_facility(payload, trace_id="trace-4")
    assert result["answer"] == "no"
    assert result["confidence"] <= 0.3


def test_facility_answer_question_parsing():
    payload = {
        "facility_id": "F-1",
        "question": "Does it have CT scan and oncology services?",
        "facility": _facility(),
    }
    result = answer_facility(payload, trace_id="trace-5")
    assert "IMAGING_CT" in result["present"]
    assert "ONC_GENERAL" in result["present"]
