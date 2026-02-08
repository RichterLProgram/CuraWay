from __future__ import annotations

from typing import Dict, List

from src.geo.osrm_client import get_travel_time_minutes


def estimate_travel_time_minutes(distance_km: float, speed_kmph: float = 40) -> int:
    if speed_kmph <= 0:
        return 0
    return int(round((distance_km / speed_kmph) * 60))


def build_travel_time_bands(
    facility_points: List[Dict],
    speed_kmph: float = 40,
    bands: List[int] | None = None,
    origin: Dict[str, float] | None = None,
) -> Dict[str, int]:
    bands = bands or [60, 120, 240]
    counts = {str(band): 0 for band in bands}
    for facility in facility_points:
        if origin and "lat" in facility and "lng" in facility:
            routing = get_travel_time_minutes(
                origin,
                {"lat": float(facility["lat"]), "lng": float(facility["lng"])},
                speed_kmph=speed_kmph,
            )
            minutes = int(routing.get("minutes") or 0)
        else:
            distance = float(facility.get("distance_km", 0))
            minutes = estimate_travel_time_minutes(distance, speed_kmph=speed_kmph)
        for band in bands:
            if minutes <= band:
                counts[str(band)] += 1
    return counts
