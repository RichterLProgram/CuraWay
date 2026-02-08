from src.intelligence.gap_detection import detect_gaps


def _demand(required=None, urgency=5):
    return {
        "demand_id": "D-001",
        "diagnosis": "lung cancer",
        "stage": "IV",
        "biomarkers": ["EGFR positive"],
        "location": {"lat": 5.6, "lon": -0.1, "region": "Greater Accra"},
        "urgency": urgency,
        "required_capabilities": required or ["ONC_GENERAL", "IMAGING_CT"],
    }


def _facility(capabilities, verdict="plausible", lat=5.61, lon=-0.09):
    return {
        "facility_id": "F-001",
        "name": "Test Facility",
        "location": {"lat": lat, "lon": lon, "region": "Greater Accra"},
        "capabilities": capabilities,
        "validation": {"verdict": verdict, "score": 0.9, "issues": []},
    }


def test_gap_detection_low_desert_score_when_covered():
    demand = _demand(required=["ONC_GENERAL", "IMAGING_CT"])
    supply = [_facility(["ONC_GENERAL", "IMAGING_CT", "SPECIALIST_RADIOLOGY"])]
    result = detect_gaps(demand, supply, {"threshold": 0.6})
    gap = result["gaps"][0]
    assert gap["desert_score"] < 0.3
    assert len(gap["candidate_facilities"]) == 1


def test_gap_detection_missing_capability_gap():
    demand = _demand(required=["ONC_GENERAL", "IMAGING_CT"])
    supply = [_facility(["ONC_GENERAL"])]
    result = detect_gaps(demand, supply, {"threshold": 0.6})
    gap = result["gaps"][0]
    assert "IMAGING_CT" in gap["missing_capabilities"]


def test_gap_detection_ignores_impossible_facility():
    demand = _demand(required=["ONC_GENERAL", "IMAGING_CT"])
    supply = [_facility(["ONC_GENERAL", "IMAGING_CT"], verdict="impossible")]
    result = detect_gaps(demand, supply, {"threshold": 0.1})
    gap = result["gaps"][0]
    assert gap["candidate_facilities"] == []


def test_gap_detection_high_urgency_no_facility_recommend_invest():
    demand = _demand(required=["ONC_GENERAL", "IMAGING_CT"], urgency=10)
    result = detect_gaps(demand, [], {"radius_km": 50, "threshold": 0.6})
    gap = result["gaps"][0]
    recs = result["recommendations"]
    assert gap["desert_score"] >= 0.7
    assert any(rec["type"] == "invest" for rec in recs)
