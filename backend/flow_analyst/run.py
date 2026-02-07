#!/usr/bin/env python3
"""Run the analyst flow (Medical Deserts + Demand)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipelines.analyst import run_analyst_pipeline


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    input_dir = root / "input" / "analyst"
    output_dir = root / "output"
    demand_csv = root / "input" / "demand_points.csv"
    demand_patient_json = root / "output" / "demand_points_from_patients.json"
    skip = {"README.txt", "README.md"}

    print("CancerCompass – Analyst Flow")
    print("-" * 50)
    print(f"Input: {input_dir}")

    analyst_api = run_analyst_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        demand_csv=demand_csv,
        demand_patient_json=demand_patient_json,
        skip_names=skip,
    )
    if not analyst_api.pins and not analyst_api.heatmap:
        print("No analyst data produced.")
        sys.exit(0)
    print("Outputs written to backend/output/")


if __name__ == "__main__":
    main()
