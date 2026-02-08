from src.intelligence.planner import plan_actions


def _demand(urgency=7, required=None):
    return {
        "diagnosis": "lung cancer",
        "stage": "IV",
        "biomarkers": [],
        "location": {"lat": 5.6, "lon": -0.1, "region": "Greater Accra"},
        "urgency": urgency,
        "required_capabilities": required or ["ONC_GENERAL", "IMAGING_CT"],
    }


def _facility(
    facility_id="F-001",
    capabilities=None,
    verdict="plausible",
    lat=5.61,
    lon=-0.09,
):
    return {
        "facility_id": facility_id,
        "name": "Test Facility",
        "location": {"lat": lat, "lon": lon, "region": "Greater Accra"},
        "capabilities": capabilities or [
            {"name": "CT scan", "capability_code": "IMAGING_CT", "citation_ids": ["c1"]},
            {"name": "Oncology", "capability_code": "ONC_GENERAL", "citation_ids": ["c2"]},
        ],
        "validation": {"verdict": verdict, "score": 0.9, "issues": []},
    }


def test_planner_route_patient_high_priority():
    payload = {"demand": _demand(urgency=9), "supply": [_facility()]}
    result = plan_actions(payload, trace_id="trace-1")
    assert result["immediate"]
    card = result["immediate"][0]
    assert card["type"] == "route_patient"
    assert card["priority"] == "high"


def test_planner_refer_for_partial_coverage():
    partial = _facility(
        capabilities=[
            {"name": "Oncology", "capability_code": "ONC_GENERAL", "citation_ids": []}
        ]
    )
    payload = {"demand": _demand(required=["ONC_GENERAL", "IMAGING_CT"]), "supply": [partial]}
    result = plan_actions(payload, trace_id="trace-2")
    assert result["near_term"]
    assert any(card["type"] == "refer" for card in result["near_term"])


def test_planner_staffing_when_suspicious():
    suspicious = _facility(verdict="suspicious")
    payload = {"demand": _demand(), "supply": [suspicious]}
    result = plan_actions(payload, trace_id="trace-3")
    assert result["near_term"]
    assert any(card["type"] == "staffing" for card in result["near_term"])


def test_planner_invest_when_no_facility():
    payload = {"demand": _demand(urgency=10), "supply": []}
    result = plan_actions(payload, trace_id="trace-4")
    assert result["invest"]
    assert any(card["type"] == "invest" for card in result["invest"])
