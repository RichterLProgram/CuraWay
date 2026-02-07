"""Patient flow pipeline (CancerCompass)."""

from pathlib import Path
from typing import List, Optional, Set

from app.io import load_documents, write_json
from clinical_trials.pipeline import run_trial_matching


def run_cancercompass_pipeline(
    input_dir: Path,
    output_dir: Path,
    skip_names: Set[str],
) -> List[object]:
    documents = load_documents(input_dir, skip_names=skip_names)
    results = run_trial_matching(documents)
    output_dir.mkdir(exist_ok=True)

    write_json(output_dir / "trial_matching_result.json", [r.model_dump() for r in results])
    write_json(
        output_dir / "trial_matching_top3.json",
        [r.model_dump(include={"top_matches", "query", "patient_profile"}) for r in results],
    )
    write_json(
        output_dir / "trial_matching_trace.json",
        [r.model_dump(include={"agent_trace", "extraction_method"}) for r in results],
    )

    patient_api = [
        {
            "patient_profile": r.patient_profile.model_dump(),
            "top_matches": r.top_matches,
            "map_pins": _build_map_pins(r),
        }
        for r in results
    ]
    write_json(output_dir / "patient_api.json", patient_api)

    demand = []
    for idx, result in enumerate(results, start=1):
        loc = result.patient_profile.location
        if loc and loc.latitude is not None and loc.longitude is not None:
            demand.append(
                {
                    "point_id": f"demand-patient-{idx:03d}",
                    "label": loc.label or f"Patient search {idx}",
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "source": "patient_search",
                    "note": f"Query: {result.query}",
                }
            )
    write_json(output_dir / "demand_points_from_patients.json", demand)
    return results


def _build_map_pins(result) -> List[dict]:
    pins = []
    for match in result.matches[:3]:
        loc = _best_location(match.trial, result.patient_profile.location)
        if not loc:
            continue
        pins.append(
            {
                "trial_id": match.trial.nct_id,
                "title": match.trial.title,
                "phase": match.trial.phase,
                "status": match.trial.status,
                "match_score": match.match_score,
                "distance_km": match.distance_km,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "label": loc.name or loc.city or "Trial Site",
            }
        )
    return pins


def _best_location(trial, patient_location) -> Optional[object]:
    locations = [loc for loc in trial.locations if loc.latitude is not None and loc.longitude is not None]
    if not locations:
        return None
    if not patient_location or patient_location.latitude is None or patient_location.longitude is None:
        return locations[0]
    return min(
        locations,
        key=lambda loc: _haversine_km(
            patient_location.latitude,
            patient_location.longitude,
            loc.latitude,
            loc.longitude,
        ),
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math

    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))
