import os

from src.shared.models import Citation, CitationLocator, CitationSpan
from src.supply.evidence_index import build_evidence_index, find_evidence_for_code
from src.validation.anomaly_agent import validate_supply


def test_find_evidence_for_code_matches_synonym():
    citation = Citation(
        citation_id="c1",
        source_doc_id="doc",
        source_type="text",
        locator=CitationLocator(chunk_id="chunk_0"),
        span=CitationSpan(start_char=0, end_char=6),
        quote="CT scan",
        confidence=0.9,
    )
    chunks = [
        {
            "chunk_id": "chunk_0",
            "source_doc_id": "doc",
            "text_snippet": "CT scan available",
            "locator": {"chunk_id": "chunk_0"},
        }
    ]
    index = build_evidence_index(chunks, [citation])
    matches = find_evidence_for_code("IMAGING_CT", index)
    assert "c1" in matches


def test_validator_attaches_citations_on_rule_violation():
    os.environ["LLM_DISABLED"] = "true"
    supply = {
        "facility_id": "fac-1",
        "name": "Test",
        "location": {"lat": 1, "lng": 1, "region": "X"},
        "capabilities": [
            {"name": "CT scan", "capability_code": "IMAGING_CT", "citation_ids": ["c1"]}
        ],
        "equipment": [],
        "specialists": [],
        "coverage_score": 10,
        "evidence_index": {
            "chunk_0": {
                "chunk_id": "chunk_0",
                "source_doc_id": "doc",
                "text_snippet": "CT scan available",
                "locator": {"chunk_id": "chunk_0"},
                "citation_ids": ["c1"],
            }
        },
    }
    result = validate_supply(supply)
    assert any(
        issue.code == "CT_MRI_REQUIRES_RADIOLOGY" and issue.evidence
        for issue in result.issues
    )
