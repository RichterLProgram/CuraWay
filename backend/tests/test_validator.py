import os

from src.validation.anomaly_agent import validate_supply


def _base_supply():
    return {
        "facility_id": "fac-001",
        "name": "Example Hospital",
        "location": {"lat": 5.6, "lng": -0.1, "region": "Accra"},
        "capabilities": [
            "CT scan",
            "MRI",
            "Surgery",
            "ICU",
            "Blood transfusion",
        ],
        "equipment": [
            "Operating theatre",
            "Ventilator",
            "Blood bank",
        ],
        "specialists": [
            "Radiologist",
            "Anesthesiologist",
        ],
        "coverage_score": 80,
        "radiologist_count": 1,
        "anesthesia_staff": 2,
        "ventilators": 3,
        "critical_care_staff": 4,
        "bed_count": 10,
        "staff_count": 40,
    }


def test_validator_plausible():
    os.environ["LLM_DISABLED"] = "true"
    supply = _base_supply()
    result = validate_supply(supply)
    assert result.verdict == "plausible"
    assert result.issue_count_by_severity["error"] == 0
    assert result.issue_count_by_severity["warning"] == 0


def test_validator_suspicious_missing_radiology():
    os.environ["LLM_DISABLED"] = "true"
    supply = _base_supply()
    supply["specialists"] = []
    supply["radiologist_count"] = 0
    result = validate_supply(supply)
    assert result.verdict == "suspicious"
    assert any(issue.code == "CT_MRI_REQUIRES_RADIOLOGY" for issue in result.issues)


def test_validator_impossible_contradiction():
    os.environ["LLM_DISABLED"] = "true"
    supply = _base_supply()
    supply["capabilities"].append("No imaging available")
    result = validate_supply(supply)
    assert result.verdict == "impossible"
    assert any(issue.code == "NO_IMAGING_CONTRADICTION" for issue in result.issues)


def test_validator_missing_required_field():
    os.environ["LLM_DISABLED"] = "true"
    supply = _base_supply()
    supply.pop("name")
    result = validate_supply(supply)
    assert result.verdict == "impossible"
    assert any(issue.code == "MISSING_REQUIRED_FIELD" for issue in result.issues)


def test_validator_type_mismatch():
    os.environ["LLM_DISABLED"] = "true"
    supply = _base_supply()
    supply["capabilities"] = "CT scan"
    result = validate_supply(supply)
    assert result.verdict == "impossible"
    assert any(issue.code == "TYPE_MISMATCH" for issue in result.issues)


def test_validator_low_confidence():
    os.environ["LLM_DISABLED"] = "true"
    supply = _base_supply()
    supply["confidence"] = {"capabilities": 0.2}
    result = validate_supply(supply)
    assert result.verdict == "suspicious"
    assert any(issue.code == "LOW_CONFIDENCE_FIELD" for issue in result.issues)
