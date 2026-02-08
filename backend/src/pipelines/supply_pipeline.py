from __future__ import annotations

import csv
import os
from typing import List, Mapping

from src.ai.llm_extractors import extract_facility_from_csv_row
from src.shared.models import FacilityCapabilities
from src.shared.utils import load_text_files, write_json
from src.supply.facility_parser import parse_facility_document
from src.analytics.desert_scoring import score_deserts
from src.observability.tracing import create_trace_id


def _facility_from_csv(
    row: Mapping[str, str],
    row_index: int,
    source_doc_id: str,
) -> FacilityCapabilities:
    return extract_facility_from_csv_row(
        row, row_index=row_index, source_doc_id=source_doc_id
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
            facilities.append(
                _facility_from_csv(row, row_index=index, source_doc_id=os.path.basename(csv_path))
            )

    if output_path:
        write_json(output_path, [item.model_dump() for item in facilities])

    return facilities


def score_supply_deserts(
    facilities: List[FacilityCapabilities],
    capability_target: str,
    region: dict | None = None,
    max_distance_km: float = 200.0,
    trace_id: str | None = None,
) -> dict:
    payload = {
        "facilities": [item.model_dump() for item in facilities],
        "capability_target": capability_target,
        "region": region,
        "max_distance_km": max_distance_km,
    }
    return score_deserts(payload, trace_id=trace_id or create_trace_id())
