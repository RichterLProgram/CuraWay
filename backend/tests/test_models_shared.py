"""Tests for models/shared.py"""
import pytest
from pydantic import ValidationError

from features.models.shared import (
    EvidenceSnippet,
    CapabilityDecision,
    RegionalRiskLevel,
    FacilityWithCapabilityDecisions,
    RegionalAssessment,
)


class TestEvidenceSnippet:
    def test_valid(self):
        e = EvidenceSnippet(text="CT scanner", document_id="doc1", chunk_id="c1")
        assert e.text == "CT scanner"
        assert e.document_id == "doc1"
        assert e.chunk_id == "c1"

    def test_empty_text_fails(self):
        with pytest.raises(ValidationError):
            EvidenceSnippet(text="", document_id="d", chunk_id="c")

    def test_empty_document_id_fails(self):
        with pytest.raises(ValidationError):
            EvidenceSnippet(text="x", document_id="", chunk_id="c")

    def test_empty_chunk_id_fails(self):
        with pytest.raises(ValidationError):
            EvidenceSnippet(text="x", document_id="d", chunk_id="")

    def test_model_dump(self):
        e = EvidenceSnippet(text="x", document_id="d", chunk_id="c")
        d = e.model_dump()
        assert d["text"] == "x"
        assert d["document_id"] == "d"
        assert d["chunk_id"] == "c"


class TestCapabilityDecision:
    def test_valid(self):
        d = CapabilityDecision(
            value=True,
            confidence=0.8,
            decision_reason="direct_evidence",
            evidence=[EvidenceSnippet(text="x", document_id="d", chunk_id="c")],
        )
        assert d.value is True
        assert len(d.evidence) == 1

    def test_all_decision_reasons(self):
        for reason in ("direct_evidence", "insufficient_evidence", "conflicting_evidence", "suspicious_claim"):
            d = CapabilityDecision(
                value=False,
                confidence=0.0,
                decision_reason=reason,
                evidence=[],
            )
            assert d.decision_reason == reason

    def test_invalid_decision_reason_fails(self):
        with pytest.raises(ValidationError):
            CapabilityDecision(
                value=False,
                confidence=0.0,
                decision_reason="invalid_reason",
                evidence=[],
            )

    def test_empty_evidence_list(self):
        d = CapabilityDecision(
            value=False,
            confidence=0.0,
            decision_reason="insufficient_evidence",
            evidence=[],
        )
        assert d.evidence == []


class TestRegionalRiskLevel:
    def test_levels(self):
        for level in ("low", "medium", "high"):
            r = RegionalRiskLevel(level=level)
            assert r.level == level

    def test_invalid_level_fails(self):
        with pytest.raises(ValidationError):
            RegionalRiskLevel(level="invalid")


class TestFacilityWithCapabilityDecisions:
    def test_valid(self):
        f = FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region="North",
            capability_decisions={"ct_scanner": {"value": True}},
        )
        assert f.facility_id == "FAC-001"
        assert f.region == "North"

    def test_empty_facility_id_fails(self):
        with pytest.raises(ValidationError):
            FacilityWithCapabilityDecisions(
                facility_id="",
                region="North",
                capability_decisions={},
            )

    def test_region_optional(self):
        f = FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region=None,
            capability_decisions={},
        )
        assert f.region is None

    def test_empty_capability_decisions(self):
        f = FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region="North",
            capability_decisions={},
        )
        assert f.capability_decisions == {}


class TestRegionalAssessment:
    def test_valid(self):
        r = RegionalAssessment(
            region="North",
            coverage_score=0.5,
            risk_level=RegionalRiskLevel(level="medium"),
            explanation="Test",
            facility_ids=["FAC-001"],
        )
        assert r.region == "North"
        assert r.risk_level.level == "medium"

    def test_empty_facility_ids(self):
        r = RegionalAssessment(
            region="South",
            coverage_score=0.0,
            risk_level=RegionalRiskLevel(level="high"),
            explanation="No facilities",
            facility_ids=[],
        )
        assert r.facility_ids == []

    def test_coverage_score_bounds(self):
        r = RegionalAssessment(
            region="X",
            coverage_score=1.0,
            risk_level=RegionalRiskLevel(level="low"),
            explanation="Full coverage",
            facility_ids=["FAC-001"],
        )
        assert r.coverage_score == 1.0
