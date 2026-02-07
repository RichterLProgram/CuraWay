#!/usr/bin/env python3
"""Run the patient flow (CancerCompass)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipelines.cancercompass import run_cancercompass_pipeline


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    input_dir = root / "input"
    output_dir = root / "output"
    skip = {"README.txt", "README.md", "Virtue Foundation Ghana v0.3 - Sheet1.csv"}

    print("CancerCompass – Patient Flow")
    print("-" * 50)
    print(f"Input: {input_dir}")

    results = run_cancercompass_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        skip_names=skip,
    )
    if not results:
        print("No supported documents found.")
        sys.exit(0)
    print("Outputs written to backend/output/")


if __name__ == "__main__":
    main()
