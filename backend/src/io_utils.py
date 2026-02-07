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
            docs.append(_format_document_text(path, content.strip()))
    return docs


def write_json(path: Path, payload: object) -> None:
    path.write_text(_to_json(payload), encoding="utf-8")


def _to_json(payload: object) -> str:
    import json

    return json.dumps(payload, indent=2, ensure_ascii=False)


def _format_document_text(path: Path, content: str) -> str:
    """
    Add a stable document_id header and line numbers for evidence citations.
    JSON files are passed through unchanged to allow pre-extracted payloads.
    """
    if path.suffix.lower() == ".json":
        return content
    doc_id = path.stem
    numbered = _add_line_numbers(content)
    return f"DOCUMENT_ID: {doc_id}\n{numbered}"


def _add_line_numbers(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return text
    width = max(4, len(str(len(lines))))
    numbered = [f"L{str(idx + 1).zfill(width)}|{line}" for idx, line in enumerate(lines)]
    return "\n".join(numbered)
