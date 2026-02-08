from src.shared.models import FacilityCapabilities, FacilityLocation
from src.supply.citations import attach_row_citations, attach_text_citations


def test_text_citation_for_ct_scan():
    text = "Facility offers CT scan and MRI for diagnostics."
    supply = FacilityCapabilities(
        facility_id="fac-1",
        name="Test Facility",
        location=FacilityLocation(lat=5.6, lng=-0.1, region="Accra"),
        capabilities=["CT scan", "MRI"],
        equipment=[],
        specialists=[],
        coverage_score=50,
    )
    supply = attach_text_citations(supply, text, source_doc_id="doc-1")
    ct_entry = next(entry for entry in supply.capabilities if entry.name == "CT scan")
    assert ct_entry.citation_ids
    citation = next(
        item for item in supply.citations if item.citation_id == ct_entry.citation_ids[0]
    )
    assert "CT" in citation.quote


def test_table_row_citation_locator():
    supply = FacilityCapabilities(
        facility_id="fac-2",
        name="CSV Facility",
        location=FacilityLocation(lat=5.6, lng=-0.1, region="Accra"),
        capabilities=["Dialysis"],
        equipment=["X-ray"],
        specialists=["Radiologist"],
        coverage_score=40,
    )
    supply = attach_row_citations(
        supply,
        row_index=4,
        source_doc_id="facilities.csv",
        row_values={"Services": "Dialysis", "Equipment": "X-ray", "Staff": "Radiologist"},
    )
    assert supply.citations
    assert all(item.locator.row == 4 for item in supply.citations)
    assert all(item.locator.col for item in supply.citations)
    assert all(entry.evidence for entry in supply.capabilities + supply.equipment + supply.specialists)
