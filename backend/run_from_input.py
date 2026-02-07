#!/usr/bin/env python3
"""Process all medical reports from the input folder."""

import json
import sys
from pathlib import Path

# Backend-Root als Modulpfad
sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestration.pipeline import run_pipeline, _demo_llm_extractor
from file_loader import extract_text, get_supported_extensions

INPUT_DIR = Path(__file__).resolve().parent / "input"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SKIP_NAMES = {"README.txt", "README.md"}


def load_documents() -> list[str]:
    """Liest alle unterstützten Dateien aus input/ ein."""
    if not INPUT_DIR.is_dir():
        print(f"Fehler: Input-Verzeichnis fehlt: {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    supported = get_supported_extensions()
    docs: list[str] = []
    files = sorted(INPUT_DIR.iterdir(), key=lambda p: p.name)
    for p in files:
        if p.suffix.lower() not in supported or not p.is_file():
            continue
        if p.name in SKIP_NAMES:
            continue
        content = extract_text(p)
        if content and content.strip():
            docs.append(content.strip())
            print(f"  + {p.name}")
    return docs


def main() -> None:
    print("CancerCompass – Facility IDP Pipeline")
    print("-" * 50)
    print(f"Input: {INPUT_DIR}")
    print("Loading documents...")

    documents = load_documents()
    if not documents:
        print("\nNo supported files found in input/.")
        print("Supported: .txt, .json, .csv, .md, .docx, .xlsx, .xls, .pdf, .odt, .rtf, .xml")
        print("Optional (pip install): python-docx, openpyxl, xlrd, pypdf, odfpy")
        print("Place reports in backend/input/ and run again.")
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
