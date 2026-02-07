#!/usr/bin/env python3
"""Run the Analyst flow (Medical Deserts + Demand)."""

import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from pipelines.analyst import run_analyst_pipeline

INPUT_DIR = root / "input" / "analyst"
OUTPUT_DIR = root / "output"
DEMAND_CSV = root / "input" / "analyst" / "demand_points.csv"
DEMAND_PATIENT_JSON = root / "output" / "demand_points_from_patients.json"
SKIP_NAMES = {"README.txt", "README.md"}


def main() -> None:
    print("CancerCompass – Analyst Flow")
    print("-" * 50)
    print(f"Input: {INPUT_DIR}")
    print("Loading facility documents...")

    extractor_mode = os.getenv("LLM_EXTRACTOR_MODE", "demo").lower()
    print(f"LLM extractor mode: {extractor_mode}")

    try:
        analyst_api = run_analyst_pipeline(
            input_dir=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            demand_csv=DEMAND_CSV,
            demand_patient_json=DEMAND_PATIENT_JSON,
            skip_names=SKIP_NAMES,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if not analyst_api.pins and not analyst_api.heatmap:
        print("No analyst data produced.")
        sys.exit(0)

    print("Outputs written to backend/output/")


if __name__ == "__main__":
    main()
