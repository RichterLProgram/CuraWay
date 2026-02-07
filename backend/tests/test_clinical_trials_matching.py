"""Tests for clinical trials matching helpers."""

import pytest

from features.clinical_trials.matching import (
    _apply_phase_boost,
    _distance_to_closest_site,
    _excludes_brain_mets,
    _find_biomarker_requirements,
    _find_ecog_max,
    _find_max_prior_therapies,
    _rank_matches,
)
from features.clinical_trials.models import TrialLocation, TrialMatch, TrialRecord
from features.patient.profile import PatientLocation, PatientProfile


def test_find_biomarker_requirements():
    criteria = "Eligibility requires EGFR mutation and PD-L1 expression, BRCA1 allowed."
    markers = _find_biomarker_requirements(criteria.lower())
    assert "EGFR" in markers
    assert "PD-L1" in markers
    assert "BRCA1" in markers


def test_find_max_prior_therapies():
    assert _find_max_prior_therapies("no more than 2 prior therapies") == 2
    assert _find_max_prior_therapies("≤ 1 prior lines") == 1


def test_find_ecog_max():
    assert _find_ecog_max("ECOG performance status 0-2") == 2
    assert _find_ecog_max("ECOG 1") == 1


def test_excludes_brain_mets():
    assert _excludes_brain_mets("no active brain metastases.") is True
    assert _excludes_brain_mets("Brain metastases allowed.") is False


def test_apply_phase_boost_caps_at_one():
    assert _apply_phase_boost(0.95, "Phase 3") == 1.0
    assert _apply_phase_boost(0.90, "Phase II") == pytest.approx(0.94)
    assert _apply_phase_boost(0.5, None) == 0.5


def test_distance_to_closest_site():
    patient = PatientProfile(
        location=PatientLocation(latitude=52.52, longitude=13.405, label="Berlin")
    )
    trial = TrialRecord(
        nct_id="NCT0001",
        title="Test",
        locations=[
            TrialLocation(latitude=48.1351, longitude=11.5820),  # Munich
            TrialLocation(latitude=52.52, longitude=13.405),     # Berlin
        ],
    )
    distance = _distance_to_closest_site(patient, trial)
    assert distance is not None
    assert distance < 1.0


def test_rank_matches_by_score_then_distance():
    trial = TrialRecord(nct_id="NCT1", title="T1")
    match_a = TrialMatch(
        trial=trial,
        match_score=0.8,
        eligibility_signals=[],
        distance_km=100.0,
    )
    match_b = TrialMatch(
        trial=trial,
        match_score=0.8,
        eligibility_signals=[],
        distance_km=None,
    )
    ranked = _rank_matches([match_b, match_a])
    assert ranked[0] is match_a
