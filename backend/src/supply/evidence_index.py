from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.ontology.normalize import load_ontology
from src.shared.models import Citation


def build_evidence_index(
    chunks: Iterable[Dict[str, Any]],
    citations: Iterable[Citation],
) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if not chunk_id:
            continue
        index[chunk_id] = {
            "chunk_id": chunk_id,
            "source_doc_id": chunk.get("source_doc_id"),
            "text_snippet": _clip(chunk.get("text_snippet", "")),
            "locator": chunk.get("locator", {}),
            "citation_ids": [],
        }

    for citation in citations:
        chunk_id = citation.locator.chunk_id if citation.locator else None
        if not chunk_id:
            continue
        if chunk_id not in index:
            index[chunk_id] = {
                "chunk_id": chunk_id,
                "source_doc_id": citation.source_doc_id,
                "text_snippet": _clip(citation.quote),
                "locator": citation.locator.model_dump(),
                "citation_ids": [],
            }
        index[chunk_id]["citation_ids"].append(citation.citation_id)

    return index


def find_evidence_for_code(
    code: str,
    evidence_index: Dict[str, Dict[str, Any]],
) -> List[str]:
    ontology = load_ontology()
    info = (ontology.get("capabilities") or {}).get(code, {})
    synonyms = [info.get("display_name", code)] + list(info.get("synonyms", []))
    synonyms_lower = [str(item).lower() for item in synonyms if item]

    matched: List[str] = []
    for chunk_id, chunk in evidence_index.items():
        text = str(chunk.get("text_snippet", "")).lower()
        if not text:
            continue
        if any(syn in text for syn in synonyms_lower):
            matched.extend(chunk.get("citation_ids", []))
    return list(dict.fromkeys([cid for cid in matched if cid]))


def _clip(text: Optional[str], limit: int = 200) -> str:
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
