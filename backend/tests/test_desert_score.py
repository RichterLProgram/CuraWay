import os

from src.analytics.desert_scoring import score_deserts


def _entry(code: str, row_id: int):
    return {
        "name": code,
        "capability_code": code,
        "evidence": {
            "source_row_id": row_id,
            "source_column_name": "capability",
            "snippet": f"{code} available",
        },
    }


def _facility(fid: str, lat: float, lon: float, entries):
    return {
        "facility_id": fid,
        "name": f"Facility {fid}",
        "location": {"lat": lat, "lon": lon, "region": "Region"},
        "capabilities": entries,
        "canonical_capabilities": [entry["capability_code"] for entry in entries],
        "citations": [],
    }


def test_desert_score_pipeline_metrics():
    os.environ["LLM_DISABLED"] = "true"
    payload = {
        "capability_target": "IMAGING_CT",
        "facilities": [
            _facility(
                "A",
                0.0,
                0.0,
                [_entry("IMAGING_CT", 1), _entry("SPECIALIST_RADIOLOGY", 2)],
            ),
            _facility("B", 0.0, 1.0, []),
            _facility("C", 0.0, 2.0, [_entry("IMAGING_CT", 3)]),
        ],
        "max_distance_km": 200,
    }
    result = score_deserts(payload, trace_id="trace-desert-1")
    scores = {item["facility_id"]: item for item in result["scores"]}

    assert scores["A"]["distance_km_to_nearest_capable"] == 0.0
    assert scores["B"]["distance_km_to_nearest_capable"] > scores["A"]["distance_km_to_nearest_capable"]
    assert "SPECIALIST_RADIOLOGY" in scores["C"]["missing_prerequisites"]

    for score in scores.values():
        assert score["explanation"]
        assert 0.0 <= score["confidence"] <= 1.0
        evidence = score["evidence"]
        assert any(item.get("row_id") is not None for item in evidence)
        row_ids = [item.get("row_id") for item in evidence if item.get("row_id") is not None]
        assert any(f"[row {row_id}]" in score["explanation"] for row_id in row_ids)
