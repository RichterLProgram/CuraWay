import os

from src.ontology.normalize import normalize_supply
from src.shared.models import FacilityCapabilities, FacilityLocation
from src.validation.anomaly_agent import validate_supply


def test_negation_detection_flags_contradiction():
    os.environ["LLM_DISABLED"] = "true"
    text = "Facility has no CT scan capability."
    supply = FacilityCapabilities(
        facility_id="fac-1",
        name="Test",
        location=FacilityLocation(lat=1, lng=1, region="X"),
        capabilities=["CT scan"],
        equipment=[],
        specialists=[],
        coverage_score=10,
    )
    supply = normalize_supply(supply, source_text=text)
    result = validate_supply(supply.model_dump())
    assert any(issue.code == "CONTRADICTION_NEGATED_CLAIM" for issue in result.issues)
