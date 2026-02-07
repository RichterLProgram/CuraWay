#!/usr/bin/env python3
"""Run the CancerCompass patient flow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.pipelines.cancercompass import run_cancercompass_pipeline

INPUT_DIR = Path(__file__).resolve().parent / "input"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SKIP_NAMES = {"README.txt", "README.md", "Virtue Foundation Ghana v0.3 - Sheet1.csv"}


def main() -> None:
    print("CancerCompass – Patient Flow")
    print("-" * 50)
    print(f"Input: {INPUT_DIR}")
    print("Loading documents...")

    try:
        results = run_cancercompass_pipeline(
            input_dir=INPUT_DIR,
            output_dir=OUTPUT_DIR,
            skip_names=SKIP_NAMES,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if not results:
        print("No supported documents found in input/.")
        sys.exit(0)

    print("Outputs written to backend/output/")


if __name__ == "__main__":
    main()
