"""Optional travel-time routing (OSRM) with fallback."""

from __future__ import annotations

import json
import os
from typing import Optional
from urllib import request


def estimate_travel_time_minutes(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    fallback_km: Optional[float] = None,
) -> Optional[float]:
    osrm_url = os.getenv("OSRM_URL")
    if osrm_url:
        duration = _osrm_duration(osrm_url, origin_lat, origin_lon, dest_lat, dest_lon)
        if duration is not None:
            return round(duration / 60.0, 1)

    if fallback_km is None:
        fallback_km = _haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    if fallback_km is None:
        return None
    return round((fallback_km / 50.0) * 60.0, 1)


def _osrm_duration(
    base_url: str,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> Optional[float]:
    try:
        url = (
            f"{base_url.rstrip('/')}/route/v1/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"
        )
        with request.urlopen(url, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        routes = payload.get("routes") or []
        if not routes:
            return None
        return float(routes[0].get("duration"))
    except Exception:
        return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    import math

    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
