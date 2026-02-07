#!/usr/bin/env python3
"""Process all medical reports from the input folder."""

import json
import sys
from pathlib import Path

# Backend-Root als Modulpfad
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "src"))

from pipelines.orchestration import run_pipeline, _demo_llm_extractor
from io_utils import load_documents

INPUT_DIR = root / "input" / "analyst"
OUTPUT_DIR = root / "output"
SKIP_NAMES = {"README.txt", "README.md"}


def main() -> None:
    print("CancerCompass – Facility IDP Pipeline")
    print("-" * 50)
    print(f"Input: {INPUT_DIR}")
    print("Loading documents...")

    try:
        documents = load_documents(INPUT_DIR, skip_names=SKIP_NAMES)
    except FileNotFoundError:
        print(f"Fehler: Input-Verzeichnis fehlt: {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)
    if not documents:
        print("\nNo supported files found in input/analyst/.")
        print("Supported: .txt, .json, .csv, .md, .docx, .xlsx, .xls, .pdf, .odt, .rtf, .xml")
        print("Optional (pip install): python-docx, openpyxl, xlrd, pypdf, odfpy")
        print("Place reports in backend/input/analyst/ and run again.")
        sys.exit(0)

    print(f"\n{len(documents)} document(s) found. Starting pipeline...\n")

    result = run_pipeline(documents, llm_extractor=_demo_llm_extractor)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "pipeline_result.json"
    out_path.write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    print("Result:")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
