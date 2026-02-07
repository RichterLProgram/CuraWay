"""Geokodierung für Patientenorte (OSM/Nominatim)."""

import json
import urllib.parse
import urllib.request
from typing import Optional

from features.patient.profile import PatientLocation

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CancerCompass/0.1 (trial-matching demo)"


def geocode_location(label: str) -> Optional[PatientLocation]:
    if not label or not label.strip():
        return None

    params = {
        "format": "json",
        "q": label,
        "limit": "1",
    }
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT}
    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    if not payload:
        return None

    item = payload[0]
    try:
        lat = float(item.get("lat"))
        lon = float(item.get("lon"))
    except (TypeError, ValueError):
        return None

    return PatientLocation(latitude=lat, longitude=lon, label=label)
