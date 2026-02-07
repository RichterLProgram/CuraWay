"""Minimal IO helpers."""

from pathlib import Path
from typing import Iterable, List, Optional, Set

from file_loader import extract_text, get_supported_extensions


def load_documents(
    input_dir: Path,
    skip_names: Optional[Set[str]] = None,
) -> List[str]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory missing: {input_dir}")
    supported = get_supported_extensions()
    skip = skip_names or set()
    docs: List[str] = []
    for path in sorted(input_dir.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.name in skip:
            continue
        if path.suffix.lower() not in supported:
            continue
        content = extract_text(path)
        if content and content.strip():
            docs.append(content.strip())
    return docs


def write_json(path: Path, payload: object) -> None:
    path.write_text(_to_json(payload), encoding="utf-8")


def _to_json(payload: object) -> str:
    import json

    return json.dumps(payload, indent=2, ensure_ascii=False)
