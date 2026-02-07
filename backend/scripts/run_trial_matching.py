#!/usr/bin/env python3
"""Run the CancerCompass patient flow."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from pipelines.cancercompass import run_cancercompass_pipeline

INPUT_DIR = root / "input" / "patient"
OUTPUT_DIR = root / "output"
SKIP_NAMES = {"README.txt", "README.md"}


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
