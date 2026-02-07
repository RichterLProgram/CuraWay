"""Tests for aggregation/medical_desert_assessor.py"""
import pytest

from features.models.shared import (
    FacilityWithCapabilityDecisions,
    RegionalAssessment,
)
from features.aggregation.medical_desert_assessor import assess_medical_desert


def _dec(value: bool, reason: str = "direct_evidence"):
    return {"value": value, "confidence": 0.7, "decision_reason": reason, "evidence": []}


class TestAssessMedicalDesert:
    def test_high_risk_region(self):
        fac = FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region="South",
            capability_decisions={
                "oncology_services": _dec(False),
                "ct_scanner": _dec(False),
                "mri_scanner": _dec(False),
                "pathology_lab": _dec(False),
                "chemotherapy_delivery": _dec(False),
                "icu": _dec(False),
            },
        )
        result = assess_medical_desert([fac])
        assert len(result) == 1
        assert result[0].region == "South"
        assert result[0].risk_level.level == "high"
        assert result[0].coverage_score == 0.0

    def test_low_risk_region(self):
        fac = FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region="North",
            capability_decisions={
                "oncology_services": _dec(True),
                "ct_scanner": _dec(True),
                "mri_scanner": _dec(True),
                "pathology_lab": _dec(True),
                "chemotherapy_delivery": _dec(True),
                "icu": _dec(True),
            },
        )
        result = assess_medical_desert([fac])
        assert result[0].risk_level.level == "low"
        assert result[0].coverage_score == 1.0

    def test_medium_risk(self):
        fac = FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region="North",
            capability_decisions={
                "oncology_services": _dec(True),
                "ct_scanner": _dec(True),
                "mri_scanner": _dec(False),
                "pathology_lab": _dec(False),
                "chemotherapy_delivery": _dec(False),
                "icu": _dec(False),
            },
        )
        result = assess_medical_desert([fac])
        assert result[0].risk_level.level == "medium"

    def test_grouped_by_region(self):
        fac1 = FacilityWithCapabilityDecisions(
            facility_id="FAC-001", region="North",
            capability_decisions={"oncology_services": _dec(True)},
        )
        fac2 = FacilityWithCapabilityDecisions(
            facility_id="FAC-002", region="North",
            capability_decisions={"ct_scanner": _dec(True)},
        )
        fac3 = FacilityWithCapabilityDecisions(
            facility_id="FAC-003", region="South",
            capability_decisions={},
        )
        result = assess_medical_desert([fac1, fac2, fac3])
        assert len(result) == 2
        north = next(r for r in result if r.region == "North")
        assert north.coverage_score > 0
        assert "FAC-001" in north.facility_ids
        assert "FAC-002" in north.facility_ids
