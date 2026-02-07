"""Tests for clinical_trials/geocoding.py without network calls."""

import json
from unittest.mock import Mock

import pytest

from features.clinical_trials import geocoding


def test_geocode_empty_label():
    assert geocoding.geocode_location("") is None
    assert geocoding.geocode_location("   ") is None


def test_geocode_network_error(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise OSError("network down")

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", _raise)
    assert geocoding.geocode_location("Berlin") is None


def test_geocode_parses_valid_payload(monkeypatch):
    payload = json.dumps([{"lat": "52.52", "lon": "13.405"}]).encode("utf-8")

    mock_response = Mock()
    mock_response.read.return_value = payload
    mock_response.__enter__ = lambda self: self
    mock_response.__exit__ = lambda self, exc_type, exc, tb: None

    monkeypatch.setattr(geocoding.urllib.request, "urlopen", lambda *_args, **_kwargs: mock_response)

    loc = geocoding.geocode_location("Berlin")
    assert loc is not None
    assert loc.latitude == 52.52
    assert loc.longitude == 13.405
