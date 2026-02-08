from __future__ import annotations

import csv
import json
from typing import List, Mapping

from src.shared.models import FacilityCapabilities, FacilityLocation
from src.shared.utils import infer_location, load_text_files, write_json
from src.supply.facility_parser import parse_facility_document
from src.supply.coverage_analyzer import calculate_coverage_score


def _safe_json_list(value: str) -> List[str]:
    if not value or value == "null":
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return [item.strip() for item in value.split(",") if item.strip()]


def _facility_from_csv(row: Mapping[str, str]) -> FacilityCapabilities:
    name = str(row.get("name") or "Unknown Facility")
    city = str(row.get("address_city") or "")
    region = str(row.get("address_stateOrRegion") or "")
    location_text = f"{city} {region}".strip() or "Unknown"
    lat, lng, inferred_region = infer_location(location_text)
    capabilities = _safe_json_list(str(row.get("capability") or ""))
    equipment = _safe_json_list(str(row.get("equipment") or ""))
    specialists = _safe_json_list(str(row.get("specialties") or ""))
    coverage_score = calculate_coverage_score(capabilities, equipment, specialists)

    return FacilityCapabilities(
        facility_id=str(row.get("unique_id") or row.get("pk_unique_id") or name)[:12],
        name=name,
        location=FacilityLocation(lat=lat, lng=lng, region=inferred_region),
        capabilities=capabilities,
        equipment=equipment,
        specialists=specialists,
        coverage_score=coverage_score,
    )


def run_supply_pipeline(
    input_dir: str,
    csv_path: str,
    output_path: str | None = None,
) -> List[FacilityCapabilities]:
    """
    End-to-end supply analysis using facility documents and CSV enrichment.
    """
    facilities: List[FacilityCapabilities] = []
    for _, text in load_text_files(input_dir):
        facilities.append(parse_facility_document(text))

    with open(csv_path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            if index >= 5:
                break
            facilities.append(_facility_from_csv(row))

    if output_path:
        write_json(output_path, [item.model_dump() for item in facilities])

    return facilities
