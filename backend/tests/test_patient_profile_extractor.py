"""Tests for features/patient/profile_extractor.py (rule-based path)."""

from features.patient.profile_extractor import (
    _extract_with_rules,
    _extract_biomarkers,
    _extract_ecog,
    _extract_brain_metastases,
    _extract_prior_therapy_lines,
    _extract_location,
)


def test_extract_with_rules_basic():
    text = "Patient with NSCLC stage IVB. ECOG 1. EGFR mutation."
    result = _extract_with_rules(text, document_id="doc1")
    profile = result.profile
    assert profile.cancer_type == "Non-Small Cell Lung Cancer"
    assert profile.stage == "IVB"
    assert "EGFR mutation" in profile.biomarkers
    assert profile.ecog_status == 1


def test_extract_biomarkers_aliases():
    text = "PDL1 positive, HER-2 amplified, BRCA-1 mutation."
    markers = _extract_biomarkers(text)
    assert "PD-L1" in markers
    assert "HER2" in markers
    assert "BRCA1" in markers


def test_extract_prior_therapy_lines_variants():
    assert _extract_prior_therapy_lines("2 prior systemic therapies") == 2
    assert _extract_prior_therapy_lines("Patient is in 2nd line.") == 1
    assert _extract_prior_therapy_lines("3 vorbehandlung") == 3


def test_extract_ecog_range():
    assert _extract_ecog("ECOG performance status 0-2") == 0
    assert _extract_ecog("ECOG 1") == 1


def test_extract_brain_metastases():
    assert _extract_brain_metastases("No brain metastases noted.") is False
    assert _extract_brain_metastases("Brain metastases present.") is True
    assert _extract_brain_metastases("No evidence reported.") is None


def test_extract_location_coordinates_and_label():
    loc = _extract_location("Latitude: 1.23 Longitude: 4.56")
    assert loc is not None
    assert loc.latitude == 1.23
    assert loc.longitude == 4.56

    loc2 = _extract_location("Location: Berlin")
    assert loc2 is not None
    assert loc2.label == "Berlin"
