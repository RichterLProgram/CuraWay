from __future__ import annotations

from typing import List

from src.demand.profile_extractor import extract_demand_from_text
from src.shared.models import DemandRequirements
from src.shared.utils import load_text_files, write_json


def run_demand_pipeline(input_dir: str, output_path: str | None = None) -> List[DemandRequirements]:
    """
    End-to-end demand analysis for all patient reports.
    """
    results: List[DemandRequirements] = []
    for _, text in load_text_files(input_dir):
        results.append(extract_demand_from_text(text))

    if output_path:
        write_json(output_path, [item.model_dump() for item in results])

    return results
