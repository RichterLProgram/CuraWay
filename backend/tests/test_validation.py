"""Tests for validation/anomaly_validator.py"""

import pytest

from features.validation.anomaly_validator import (
    detect_suspicious_claims,
    is_negated,
    suspicious_for_capability,
)


def test_detect_suspicious_claims_picks_sentences():
    text = (
        "We are a world-class center. "
        "Our staff is kind. "
        "State-of-the-art imaging is available!"
    )
    claims = detect_suspicious_claims(text)
    assert len(claims) == 2
    assert "world-class" in claims[0].lower()
    assert "state-of-the-art" in claims[1].lower()


@pytest.mark.parametrize(
    "text,expected",
    [
        ("No CT scanner available.", True),
        ("Patient without ICU access.", True),
        ("CT scanner available.", False),
    ],
)
def test_is_negated(text, expected):
    assert is_negated(text) is expected


def test_suspicious_for_capability_matches_keywords():
    claims = ["World-class oncology center with advanced diagnostics."]
    assert suspicious_for_capability("oncology_services", claims) is True
    assert suspicious_for_capability("mri_scanner", claims) is False
