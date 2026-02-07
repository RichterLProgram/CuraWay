#!/usr/bin/env python3
"""Run both flows and write a unified frontend shell."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from io_utils import write_json
from pipelines.analyst import run_analyst_pipeline
from pipelines.app_shell import build_app_shell
from pipelines.cancercompass import run_cancercompass_pipeline


def main() -> None:
    input_dir = root / "input" / "patient"
    analyst_dir = root / "input" / "analyst"
    output_dir = root / "output"
    demand_csv = root / "input" / "analyst" / "demand_points.csv"
    demand_patient_json = root / "output" / "demand_points_from_patients.json"

    print("CancerCompass – Unified Bundle")
    print("-" * 50)

    patient_results = run_cancercompass_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        skip_names={"README.txt", "README.md"},
    )
    analyst_api = run_analyst_pipeline(
        input_dir=analyst_dir,
        output_dir=output_dir,
        demand_csv=demand_csv,
        demand_patient_json=demand_patient_json,
        skip_names={"README.txt", "README.md"},
    )

    app_shell = build_app_shell(patient_results, analyst_api.model_dump())
    write_json(output_dir / "app_shell.json", app_shell)
    print("Outputs written to backend/output/")


if __name__ == "__main__":
    main()
