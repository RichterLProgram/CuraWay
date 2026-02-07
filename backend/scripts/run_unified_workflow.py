#!/usr/bin/env python3
"""Run patient + analyst flows and write unified outputs."""

import os
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from io_utils import write_json  # noqa: E402
from pipelines.analyst import run_analyst_pipeline  # noqa: E402
from pipelines.app_shell import build_app_shell  # noqa: E402
from pipelines.cancercompass import run_cancercompass_pipeline  # noqa: E402
from features.analyst.analytics import save_baseline  # noqa: E402


def main() -> None:
    input_dir = root / "input" / "patient"
    analyst_dir = root / "input" / "analyst"
    output_dir = root / "output"
    demand_csv = root / "input" / "analyst" / "demand_points.csv"
    demand_patient_json = root / "output" / "demand_points_from_patients.json"

    print("CancerCompass – Unified Workflow")
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

    if os.getenv("SAVE_MONITORING_BASELINE", "0") in {"1", "true", "yes"}:
        snapshot_path = output_dir / "monitoring_snapshot.json"
        baseline_path = output_dir / "monitoring_baseline.json"
        if snapshot_path.exists():
            try:
                save_baseline(baseline_path, _load_json(snapshot_path))
                print(f"Saved monitoring baseline: {baseline_path}")
            except Exception:
                print("Failed to save monitoring baseline.")

    if os.getenv("COPY_FRONTEND_ASSETS", "0") in {"1", "true", "yes"}:
        public_dir = root.parent / "frontend" / "public"
        if public_dir.exists():
            shutil.copytree(output_dir, public_dir / "data", dirs_exist_ok=True)
            print(f"Copied output JSON to {public_dir / 'data'}")

    print("Outputs written to backend/output/")


def _load_json(path: Path) -> dict:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
