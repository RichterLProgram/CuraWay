"""Load demand points from CSV or patient matching."""

import csv
import json
from pathlib import Path
from typing import Iterable, List

from features.analyst.models import DemandPoint
from features.clinical_trials.models import TrialMatchingResult


def load_demand_points_csv(path: Path) -> List[DemandPoint]:
    if not path.is_file():
        return []
    points: List[DemandPoint] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            try:
                lat = float(row.get("latitude") or row.get("lat") or "")
                lon = float(row.get("longitude") or row.get("lon") or "")
            except ValueError:
                continue
            label = (row.get("label") or row.get("city") or f"Demand {idx}").strip()
            source = (row.get("source") or "manual").strip()
            note = (row.get("note") or "").strip() or None
            points.append(
                DemandPoint(
                    point_id=f"demand-csv-{idx:03d}",
                    label=label,
                    latitude=lat,
                    longitude=lon,
                    source=source,
                    note=note,
                )
            )
    return points


def load_demand_points_from_matching(
    results: Iterable[TrialMatchingResult],
) -> List[DemandPoint]:
    points: List[DemandPoint] = []
    for idx, result in enumerate(results, start=1):
        location = result.patient_profile.location
        if not location or location.latitude is None or location.longitude is None:
            continue
        label = location.label or f"Patient search {idx}"
        points.append(
            DemandPoint(
                point_id=f"demand-patient-{idx:03d}",
                label=label,
                latitude=location.latitude,
                longitude=location.longitude,
                source="patient_search",
                note=f"Query: {result.query}",
            )
        )
    return points


def load_demand_points_json(path: Path) -> List[DemandPoint]:
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    points: List[DemandPoint] = []
    if not isinstance(payload, list):
        return points
    for idx, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            continue
        try:
            lat = float(row.get("latitude") or row.get("lat") or "")
            lon = float(row.get("longitude") or row.get("lon") or "")
        except ValueError:
            continue
        points.append(
            DemandPoint(
                point_id=row.get("point_id") or f"demand-json-{idx:03d}",
                label=row.get("label") or f"Demand {idx}",
                latitude=lat,
                longitude=lon,
                source=row.get("source") or "patient_search",
                note=row.get("note"),
            )
        )
    return points
