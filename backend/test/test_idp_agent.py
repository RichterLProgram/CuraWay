"""
Unit tests for idp_agent.py
Tests models, IDPAgent, build_capability_decisions, and edge cases.
"""
import json
import pytest

# Import from parent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from idp_agent import (
    FacilityInfo,
    Capabilities,
    Metadata,
    CapabilitySchema,
    EvidenceSnippet,
    CapabilityDecision,
    IDPAgent,
    build_capability_decisions,
)


# --- Model Tests ---


class TestFacilityInfo:
    def test_valid_facility_info(self):
        f = FacilityInfo(facility_name="Test Hospital", country="Germany", region="Bavaria")
        assert f.facility_name == "Test Hospital"
        assert f.country == "Germany"
        assert f.region == "Bavaria"

    def test_empty_facility_name_fails(self):
        with pytest.raises(ValueError):
            FacilityInfo(facility_name="", country="DE")

    def test_optional_fields(self):
        f = FacilityInfo(facility_name="X", country=None, region=None)
        assert f.country is None
        assert f.region is None


class TestCapabilities:
    def test_all_bools_required(self):
        cap = Capabilities(
            oncology_services=True,
            ct_scanner=False,
            mri_scanner=True,
            pathology_lab=False,
            genomic_testing=False,
            chemotherapy_delivery=True,
            radiotherapy=False,
            icu=True,
            trial_coordinator=False,
        )
        assert cap.oncology_services is True
        assert cap.ct_scanner is False


class TestMetadata:
    def test_confidence_scores_validation(self):
        scores = {f"k{i}": 0.5 for i in range(9)}
        evidence = {f"k{i}": [] for i in range(9)}
        m = Metadata(confidence_scores=scores, extracted_evidence=evidence, suspicious_claims=[])
        assert m.confidence_scores["k0"] == 0.5

    def test_confidence_out_of_range_fails(self):
        scores = {"k0": 1.5, **{f"k{i}": 0.0 for i in range(1, 9)}}
        evidence = {f"k{i}": [] for i in range(9)}
        with pytest.raises(ValueError, match="out of range"):
            Metadata(confidence_scores=scores, extracted_evidence=evidence, suspicious_claims=[])


class TestCapabilitySchema:
    def test_alignment_validation(self):
        fi = FacilityInfo(facility_name="X")
        cap = Capabilities(
            oncology_services=False, ct_scanner=False, mri_scanner=False,
            pathology_lab=False, genomic_testing=False, chemotherapy_delivery=False,
            radiotherapy=False, icu=False, trial_coordinator=False,
        )
        keys = list(Capabilities.model_fields.keys())
        meta = Metadata(
            confidence_scores={k: 0.0 for k in keys},
            extracted_evidence={k: [] for k in keys},
            suspicious_claims=[],
        )
        schema = CapabilitySchema(facility_info=fi, capabilities=cap, metadata=meta)
        assert schema.facility_info.facility_name == "X"


class TestEvidenceSnippet:
    def test_valid_snippet(self):
        e = EvidenceSnippet(text="We have CT", document_id="doc1", chunk_id="ch1")
        assert e.text == "We have CT"

    def test_empty_text_fails(self):
        with pytest.raises(ValueError):
            EvidenceSnippet(text="", document_id="d", chunk_id="c")


# --- IDPAgent Tests ---


def mock_llm_valid(prompt: str) -> str:
    """Returns valid JSON matching expected schema."""
    return json.dumps({
        "facility_name": "Test Hospital",
        "country": "Germany",
        "region": "Berlin",
        "capabilities": {
            "oncology_services": {"value": True, "confidence": 0.8, "evidence": ["We offer oncology"]},
            "ct_scanner": {"value": True, "confidence": 0.9, "evidence": ["CT scanner available"]},
            "mri_scanner": {"value": False, "confidence": 0.0, "evidence": []},
            "pathology_lab": {"value": True, "confidence": 0.7, "evidence": ["Pathology lab"]},
            "genomic_testing": {"value": False, "confidence": 0.0, "evidence": []},
            "chemotherapy_delivery": {"value": True, "confidence": 0.75, "evidence": ["Chemo"]},
            "radiotherapy": {"value": False, "confidence": 0.0, "evidence": []},
            "icu": {"value": True, "confidence": 0.85, "evidence": ["ICU"]},
            "trial_coordinator": {"value": False, "confidence": 0.0, "evidence": []},
        },
        "suspicious_claims": [],
    })


class TestIDPAgent:
    def test_parse_facility_document_basic(self):
        agent = IDPAgent(llm_extractor=mock_llm_valid)
        text = "Test Hospital in Berlin, Germany. We have CT, MRI, oncology services."
        result = agent.parse_facility_document(text)
        assert result.facility_info.facility_name == "Test Hospital"
        assert result.capabilities.ct_scanner is True

    def test_chunk_text_empty(self):
        agent = IDPAgent(llm_extractor=mock_llm_valid)
        chunks = agent._chunk_text("")
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_chunk_text_single_paragraph(self):
        agent = IDPAgent(llm_extractor=mock_llm_valid)
        text = "One short paragraph."
        chunks = agent._chunk_text(text)
        assert len(chunks) >= 1
        assert "One short paragraph" in chunks[0]

    def test_invalid_json_raises(self):
        def bad_llm(_):
            return "not valid json {{{"
        agent = IDPAgent(llm_extractor=bad_llm)
        with pytest.raises(json.JSONDecodeError):
            agent.parse_facility_document("Some text")

    def test_value_as_string_false_bug(self):
        """Bug: LLM might return 'value': 'false' (string). bool('false') is True!"""
        def llm_returns_string_false(prompt: str) -> str:
            return json.dumps({
                "facility_name": "X",
                "country": None,
                "region": None,
                "capabilities": {
                    "oncology_services": {"value": "false", "confidence": 0.0, "evidence": []},
                    "ct_scanner": {"value": "false", "confidence": 0.0, "evidence": []},
                    "mri_scanner": {"value": "false", "confidence": 0.0, "evidence": []},
                    "pathology_lab": {"value": "false", "confidence": 0.0, "evidence": []},
                    "genomic_testing": {"value": "false", "confidence": 0.0, "evidence": []},
                    "chemotherapy_delivery": {"value": "false", "confidence": 0.0, "evidence": []},
                    "radiotherapy": {"value": "false", "confidence": 0.0, "evidence": []},
                    "icu": {"value": "false", "confidence": 0.0, "evidence": []},
                    "trial_coordinator": {"value": "false", "confidence": 0.0, "evidence": []},
                },
                "suspicious_claims": [],
            })
        agent = IDPAgent(llm_extractor=llm_returns_string_false)
        result = agent.parse_facility_document("No capabilities.")
        # If bug exists: bool("false") = True, so capabilities would be True
        assert result.capabilities.ct_scanner is False  # Expect False; bug would give True

    def test_detect_suspicious_claims(self):
        agent = IDPAgent(llm_extractor=mock_llm_valid)
        claims = agent._detect_suspicious_claims("We offer world-class care. State-of-the-art equipment.")
        assert len(claims) >= 2
        assert any("world-class" in c.lower() for c in claims)

    def test_most_common_non_empty(self):
        agent = IDPAgent(llm_extractor=mock_llm_valid)
        assert agent._most_common_non_empty(["A", "B", "A"]) == "A"
        assert agent._most_common_non_empty([]) is None
        assert agent._most_common_non_empty(["", "  ", None]) is None

    def test_dedupe_snippets(self):
        agent = IDPAgent(llm_extractor=mock_llm_valid)
        dupes = ["same", "same", "other", "  same  "]
        out = agent._dedupe_snippets(dupes)
        assert len(out) == 2
        assert "same" in out
        assert "other" in out


# --- build_capability_decisions Tests ---


class TestBuildCapabilityDecisions:
    def test_with_capability_schema(self):
        fi = FacilityInfo(facility_name="X")
        cap = Capabilities(
            oncology_services=True, ct_scanner=True, mri_scanner=False,
            pathology_lab=False, genomic_testing=False, chemotherapy_delivery=False,
            radiotherapy=False, icu=False, trial_coordinator=False,
        )
        keys = list(Capabilities.model_fields.keys())
        meta = Metadata(
            confidence_scores={k: 0.7 for k in keys},
            extracted_evidence={k: ["evidence"] if k in ("oncology_services", "ct_scanner") else [] for k in keys},
            suspicious_claims=[],
        )
        schema = CapabilitySchema(facility_info=fi, capabilities=cap, metadata=meta)
        decisions = build_capability_decisions(schema)
        assert "oncology_services" in decisions
        assert decisions["oncology_services"].value is True

    def test_with_dict_input(self):
        keys = [
            "oncology_services", "ct_scanner", "mri_scanner", "pathology_lab",
            "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator",
        ]
        d = {
            "capabilities": {k: False for k in keys},
            "metadata": {
                "confidence_scores": {k: 0.0 for k in keys},
                "extracted_evidence": {k: [] for k in keys},
                "suspicious_claims": [],
            },
        }
        decisions = build_capability_decisions(d)
        assert len(decisions) == 9

    def test_string_evidence_normalized(self):
        """Evidence can be plain strings; _normalize_evidence handles them."""
        fi = FacilityInfo(facility_name="X")
        cap = Capabilities(
            oncology_services=True, ct_scanner=False, mri_scanner=False,
            pathology_lab=False, genomic_testing=False, chemotherapy_delivery=False,
            radiotherapy=False, icu=False, trial_coordinator=False,
        )
        keys = list(Capabilities.model_fields.keys())
        meta = Metadata(
            confidence_scores={k: 0.8 for k in keys},
            extracted_evidence={
                "oncology_services": ["We have oncology"],
                **{k: [] for k in keys if k != "oncology_services"},
            },
            suspicious_claims=[],
        )
        schema = CapabilitySchema(facility_info=fi, capabilities=cap, metadata=meta)
        decisions = build_capability_decisions(schema)
        ev = decisions["oncology_services"].evidence
        assert len(ev) == 1
        assert ev[0].text == "We have oncology"
        assert ev[0].document_id == "unknown"


# --- Pydantic v2 compatibility check ---


def test_pydantic_fields_access():
    """Capabilities.model_fields is Pydantic v2 API."""
    keys = list(Capabilities.model_fields.keys())
    assert len(keys) == 9
