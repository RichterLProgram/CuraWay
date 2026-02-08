from src.supply.fallback_parse import parse_supply_fallback


def test_supply_fallback_extracts_codes():
    text = "Facility provides CT scan and MRI with oncology services."
    supply = parse_supply_fallback(text, source_doc_id="doc")
    codes = set(supply.canonical_capabilities or [])
    assert "IMAGING_CT" in codes
    assert "IMAGING_MRI" in codes
