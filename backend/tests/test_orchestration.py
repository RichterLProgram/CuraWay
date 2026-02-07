"""Tests for orchestration/pipeline.py and trace.py"""
import json
import pytest

from pipelines.orchestration import (
    run_pipeline,
    PipelineResult,
    _try_parse_idp_payload,
    _validate_pre_extracted_provenance,
    _enrich_decisions_with_provenance,
    _demo_llm_extractor,
)
from pipelines.trace import (
    build_pipeline_trace,
    PipelineTrace,
    TraceEvidenceSnippet,
    _normalize_evidence,
)


# Pre-extracted JSON with provenance (document_id, chunk_id in evidence)
def _pre_extracted_with_provenance(region: str = "North"):
    return json.dumps({
        "facility_info": {"facility_name": f"{region} Clinic", "country": "GH", "region": region},
        "capabilities": {
            "oncology_services": region == "North",
            "ct_scanner": region == "North",
            "mri_scanner": False,
            "pathology_lab": region == "North",
            "genomic_testing": False,
            "chemotherapy_delivery": False,
            "radiotherapy": False,
            "icu": region == "North",
            "trial_coordinator": False,
        },
        "metadata": {
            "confidence_scores": {k: 0.7 for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
            "extracted_evidence": {
                "oncology_services": [{"text": "oncology", "document_id": "DOC-001", "chunk_id": "c0"}] if region == "North" else [],
                "ct_scanner": [{"text": "CT", "document_id": "DOC-001", "chunk_id": "c0"}] if region == "North" else [],
                "mri_scanner": [],
                "pathology_lab": [{"text": "pathology", "document_id": "DOC-001", "chunk_id": "c0"}] if region == "North" else [],
                "genomic_testing": [],
                "chemotherapy_delivery": [],
                "radiotherapy": [],
                "icu": [{"text": "ICU", "document_id": "DOC-001", "chunk_id": "c0"}] if region == "North" else [],
                "trial_coordinator": [],
            },
            "suspicious_claims": [],
        },
    })


def _pre_extracted_empty_evidence(region: str = "South"):
    return json.dumps({
        "facility_info": {"facility_name": f"{region} Clinic", "country": "GH", "region": region},
        "capabilities": {k: False for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
        "metadata": {
            "confidence_scores": {k: 0.0 for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
            "extracted_evidence": {k: [] for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
            "suspicious_claims": [],
        },
    })


class TestPipeline:
    def test_run_pipeline_raw_text(self):
        result = run_pipeline(
            ["North Clinic has oncology and CT."],
            llm_extractor=_demo_llm_extractor,
        )
        assert isinstance(result, PipelineResult)
        assert len(result.raw_idp_output) == 1
        assert "FAC-001" in result.capability_decisions
        assert len(result.regional_assessments) >= 1

    def test_run_pipeline_pre_extracted(self):
        doc = _pre_extracted_with_provenance("North")
        result = run_pipeline([doc], llm_extractor=_demo_llm_extractor)
        assert len(result.raw_idp_output) == 1
        ev = result.capability_decisions["FAC-001"].get("oncology_services", {}).get("evidence", [])
        assert len(ev) >= 1
        assert ev[0].get("document_id") not in ("unknown", "")

    def test_evidence_provenance_enriched(self):
        raw = "North Clinic. Oncology and CT."
        result = run_pipeline([raw], llm_extractor=_demo_llm_extractor)
        dec = result.capability_decisions["FAC-001"].get("oncology_services", {})
        ev = dec.get("evidence", [])
        if ev:
            assert ev[0].get("document_id") == "DOC-001"
            assert ev[0].get("chunk_id") in ("chunk-aggregated", "chunk-0")

    def test_pre_extracted_string_evidence_fails(self):
        doc = json.dumps({
            "facility_info": {"facility_name": "X", "country": "GH", "region": "North"},
            "capabilities": {"oncology_services": True, "ct_scanner": False, "mri_scanner": False, "pathology_lab": False, "genomic_testing": False, "chemotherapy_delivery": False, "radiotherapy": False, "icu": False, "trial_coordinator": False},
            "metadata": {
                "confidence_scores": {k: 0.7 for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
                "extracted_evidence": {"oncology_services": ["plain string"], **{k: [] for k in ("ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")}},
                "suspicious_claims": [],
            },
        })
        with pytest.raises(ValueError, match="document_id"):
            run_pipeline([doc], llm_extractor=_demo_llm_extractor)

    def test_try_parse_idp_payload_valid(self):
        doc = _pre_extracted_empty_evidence()
        parsed = _try_parse_idp_payload(doc)
        assert parsed is not None
        assert "facility_info" in parsed

    def test_try_parse_idp_payload_invalid(self):
        assert _try_parse_idp_payload("not json") is None
        assert _try_parse_idp_payload('{"foo": 1}') is None


class TestTrace:
    def test_build_pipeline_trace(self):
        doc1 = _pre_extracted_with_provenance("North")
        doc2 = _pre_extracted_empty_evidence("South")
        result = run_pipeline([doc1, doc2], llm_extractor=_demo_llm_extractor)
        trace = build_pipeline_trace(result)
        assert isinstance(trace, PipelineTrace)
        assert len(trace.steps) == 3
        assert trace.steps[0].step_name == "idp_extraction"
        assert trace.steps[1].step_name == "capability_decisions"
        assert trace.steps[2].step_name == "medical_desert_assessment"

    def test_normalize_evidence_skips_unknown(self):
        raw = [{"text": "x", "document_id": "unknown", "chunk_id": "c1"}]
        out = _normalize_evidence(raw)
        assert len(out) == 0

    def test_normalize_evidence_preserves_provenance(self):
        raw = [{"text": "x", "document_id": "DOC-001", "chunk_id": "chunk-0"}]
        out = _normalize_evidence(raw)
        assert len(out) == 1
        assert out[0].document_id == "DOC-001"
        assert out[0].chunk_id == "chunk-0"
