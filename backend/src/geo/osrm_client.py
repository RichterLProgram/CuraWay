from __future__ import annotations

import os
from typing import Dict, Optional

import requests

from src.geo.haversine import haversine_km


def get_travel_time_minutes(
    origin: Dict[str, float],
    destination: Dict[str, float],
    speed_kmph: float = 40,
) -> Dict[str, Optional[float]]:
    base_url = os.getenv("OSRM_BASE_URL")
    if base_url:
        try:
            url = (
                f"{base_url.rstrip('/')}/route/v1/driving/"
                f"{origin['lng']},{origin['lat']};{destination['lng']},{destination['lat']}"
                "?overview=false"
            )
            response = requests.get(url, timeout=6)
            if response.ok:
                data = response.json()
                routes = data.get("routes") or []
                if routes:
                    duration_sec = routes[0].get("duration")
                    distance_m = routes[0].get("distance")
                    return {
                        "minutes": round(float(duration_sec) / 60, 1) if duration_sec else None,
                        "distance_km": round(float(distance_m) / 1000, 2) if distance_m else None,
                        "source": "osrm",
                    }
        except Exception:
            pass

    distance_km = haversine_km(
        float(origin["lat"]),
        float(origin["lng"]),
        float(destination["lat"]),
        float(destination["lng"]),
    )
    if speed_kmph <= 0:
        minutes = 0.0
    else:
        minutes = round((distance_km / speed_kmph) * 60, 1)
    return {
        "minutes": float(minutes),
        "distance_km": round(distance_km, 2),
        "source": "haversine",
    }
