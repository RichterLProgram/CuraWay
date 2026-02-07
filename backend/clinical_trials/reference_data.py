"""Lädt statische Backend-Referenzdaten (nicht verändern)."""

import csv
from pathlib import Path
from typing import List

from clinical_trials.models import BackendReferenceData

ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = ROOT / "input" / "Virtue Foundation Ghana v0.3 - Sheet1.csv"
SCHEME_DOC_PATH = ROOT / "tests" / "Virtue Foundation Scheme Documentation.txt"
PROMPT_MODELS_DIR = ROOT / "tests" / "prompts_and_pydantic_models"


def load_reference_data() -> BackendReferenceData:
    return BackendReferenceData(
        virtue_foundation_records=_count_csv_rows(CSV_PATH),
        scheme_doc_title=_read_first_line(SCHEME_DOC_PATH),
        prompt_model_files=_list_prompt_files(PROMPT_MODELS_DIR),
    )


def _count_csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    return max(0, len(rows) - 1)


def _read_first_line(path: Path) -> str:
    if not path.is_file():
        return ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            cleaned = line.strip()
            if cleaned:
                return cleaned
    return ""


def _list_prompt_files(path: Path) -> List[str]:
    if not path.is_dir():
        return []
    return sorted(p.name for p in path.iterdir() if p.is_file())
