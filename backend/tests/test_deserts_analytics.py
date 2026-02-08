from src.analytics.deserts import analyze_deserts


def _demand(lat, lon, required):
    return {
        "diagnosis": "lung cancer",
        "location": {"lat": lat, "lon": lon, "region": "Region"},
        "urgency": 8,
        "required_capabilities": required,
    }


def _facility(lat, lon, codes, verdict="plausible"):
    return {
        "facility_id": f"F-{lat}-{lon}",
        "name": "Facility",
        "location": {"lat": lat, "lon": lon, "region": "Region"},
        "capabilities": [{"name": code, "capability_code": code} for code in codes],
        "validation": {"verdict": verdict, "score": 0.9, "issues": []},
        "canonical_capabilities": codes,
    }


def test_deserts_single_cluster_high_score():
    payload = {
        "demands": [_demand(5.6, -0.1, ["IMAGING_CT"])],
        "supply": [],
    }
    result = analyze_deserts(payload, trace_id="trace-1")
    assert result["top_deserts"]
    assert result["top_deserts"][0]["desert_score"] >= 0.6


def test_deserts_two_clusters_ranking():
    payload = {
        "demands": [
            _demand(5.6, -0.1, ["IMAGING_CT"]),
            _demand(7.1, -1.2, ["ONC_GENERAL"]),
        ],
        "supply": [_facility(7.1, -1.2, ["ONC_GENERAL"])],
    }
    result = analyze_deserts(payload, trace_id="trace-2")
    assert len(result["top_deserts"]) >= 1
    assert result["top_deserts"][0]["desert_score"] >= result["top_deserts"][-1]["desert_score"]


def test_deserts_investment_package_when_no_facility():
    payload = {"demands": [_demand(5.6, -0.1, ["IMAGING_CT"])], "supply": []}
    result = analyze_deserts(payload, trace_id="trace-3")
    package = result["top_deserts"][0]["recommended_action_package"]
    assert "investment" in package


def test_deserts_staffing_package_when_suspicious():
    payload = {
        "demands": [_demand(5.6, -0.1, ["ONC_GENERAL"])],
        "supply": [_facility(5.6, -0.1, ["ONC_GENERAL"], verdict="suspicious")],
    }
    result = analyze_deserts(payload, trace_id="trace-4")
    package = result["top_deserts"][0]["recommended_action_package"]
    assert "staffing" in package
