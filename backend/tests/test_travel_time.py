from src.geo.travel_time import build_travel_time_bands, estimate_travel_time_minutes


def test_travel_time_increases_with_distance():
    assert estimate_travel_time_minutes(10, speed_kmph=40) < estimate_travel_time_minutes(
        50, speed_kmph=40
    )


def test_travel_time_bands_counts():
    points = [
        {"distance_km": 10},
        {"distance_km": 60},
        {"distance_km": 120},
    ]
    bands = build_travel_time_bands(points, speed_kmph=60, bands=[60, 120])
    assert bands["60"] >= 1
    assert bands["120"] >= bands["60"]


def test_gap_includes_travel_time_min():
    from src.intelligence.gap_detection import detect_gaps

    demand = {
        "diagnosis": "lung cancer",
        "location": {"lat": 5.6, "lon": -0.1, "region": "Greater Accra"},
        "urgency": 5,
        "required_capabilities": ["ONC_GENERAL"],
    }
    supply = [
        {
            "facility_id": "F-1",
            "name": "Test Facility",
            "location": {"lat": 5.61, "lon": -0.09, "region": "Greater Accra"},
            "capabilities": [{"name": "Oncology", "capability_code": "ONC_GENERAL"}],
        }
    ]
    result = detect_gaps(demand, supply, {"threshold": 0.1, "avg_speed_kmph": 40})
    facility_point = result["map"]["facility_points"][0]
    assert "travel_time_min" in facility_point
