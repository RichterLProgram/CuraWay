from __future__ import annotations

import re
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from src.shared.models import Citation, CitationLocator, CitationSpan, SupplyEntry


def attach_text_citations(
    supply: Any,
    text: str,
    source_doc_id: str,
    source_type: str = "text",
    chunk_id: Optional[str] = None,
) -> Any:
    citations: List[Citation] = list(getattr(supply, "citations", []) or [])
    supply.capabilities = _attach_list_citations(
        supply.capabilities,
        text,
        source_doc_id,
        source_type,
        chunk_id,
        citations,
    )
    supply.equipment = _attach_list_citations(
        supply.equipment,
        text,
        source_doc_id,
        source_type,
        chunk_id,
        citations,
    )
    supply.specialists = _attach_list_citations(
        supply.specialists,
        text,
        source_doc_id,
        source_type,
        chunk_id,
        citations,
    )
    supply.citations = citations
    return supply


def attach_row_citations(
    supply: Any,
    row_index: int,
    source_doc_id: str,
    row_values: Optional[Mapping[str, str]] = None,
    source_type: str = "table",
    chunk_id: Optional[str] = None,
) -> Any:
    values = row_values or {}
    quote = _short_quote(" | ".join([value for value in values.values() if value]))
    locator = CitationLocator(row=row_index, chunk_id=chunk_id)
    citations: List[Citation] = list(getattr(supply, "citations", []) or [])

    supply.capabilities = _attach_row_list(
        supply.capabilities,
        source_doc_id,
        source_type,
        locator,
        quote,
        values,
        citations,
    )
    supply.equipment = _attach_row_list(
        supply.equipment,
        source_doc_id,
        source_type,
        locator,
        quote,
        values,
        citations,
    )
    supply.specialists = _attach_row_list(
        supply.specialists,
        source_doc_id,
        source_type,
        locator,
        quote,
        values,
        citations,
    )
    supply.citations = citations
    return supply


def _attach_list_citations(
    entries: Iterable[Any],
    text: str,
    source_doc_id: str,
    source_type: str,
    chunk_id: Optional[str],
    citations: List[Citation],
) -> List[SupplyEntry]:
    updated: List[SupplyEntry] = []
    for entry in entries or []:
        name = _entry_name(entry)
        citation_ids: List[str] = []
        evidence: Optional[Dict[str, Any]] = None
        if name:
            span = _find_span(text, name)
            if span:
                citation_id = str(uuid.uuid4())
                start_char, end_char, quote = span
                citations.append(
                    Citation(
                        citation_id=citation_id,
                        source_doc_id=source_doc_id,
                        source_type=source_type,
                        locator=CitationLocator(chunk_id=chunk_id),
                        span=CitationSpan(start_char=start_char, end_char=end_char),
                        quote=quote,
                        confidence=0.9,
                    )
                )
                citation_ids.append(citation_id)
                evidence = {
                    "source_row_id": None,
                    "source_column_name": None,
                    "snippet": quote,
                }
            else:
                evidence = {
                    "source_row_id": None,
                    "source_column_name": None,
                    "snippet": _short_quote(name),
                }
        updated.append(
            SupplyEntry(name=name, citation_ids=citation_ids, evidence=evidence)
        )
    return updated


def _attach_row_list(
    entries: Iterable[Any],
    source_doc_id: str,
    source_type: str,
    locator: CitationLocator,
    quote: str,
    row_values: Mapping[str, str],
    citations: List[Citation],
) -> List[SupplyEntry]:
    updated: List[SupplyEntry] = []
    for entry in entries or []:
        name = _entry_name(entry)
        col_name, snippet = _find_row_evidence(name, row_values)
        citation_id = str(uuid.uuid4())
        citations.append(
            Citation(
                citation_id=citation_id,
                source_doc_id=source_doc_id,
                source_type=source_type,
                locator=CitationLocator(
                    row=locator.row, col=col_name, chunk_id=locator.chunk_id
                ),
                span=CitationSpan(),
                quote=snippet or quote or name,
                confidence=0.6,
            )
        )
        evidence = {
            "source_row_id": locator.row,
            "source_column_name": col_name,
            "snippet": snippet or quote or name,
        }
        updated.append(
            SupplyEntry(
                name=name,
                citation_ids=[citation_id],
                evidence=evidence,
            )
        )
    return updated


def _entry_name(entry: Any) -> str:
    if isinstance(entry, SupplyEntry):
        return entry.name
    if isinstance(entry, dict):
        return str(entry.get("name") or "")
    return str(entry)


def _find_span(text: str, value: str) -> Optional[Tuple[int, int, str]]:
    if not text or not value:
        return None
    pattern = re.escape(value.strip())
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    start, end = match.start(), match.end()
    quote = _short_quote(text[start:end], max_len=200)
    return start, end, quote


def _short_quote(text: str, max_len: int = 200) -> str:
    clipped = text.strip()
    if len(clipped) <= max_len:
        return clipped
    return clipped[: max_len - 3].rstrip() + "..."


def _find_row_evidence(
    name: str,
    row_values: Mapping[str, str],
) -> Tuple[Optional[str], Optional[str]]:
    if not row_values or not name:
        return None, None
    target = name.strip().lower()
    best_col = None
    best_snippet = None
    for col, value in row_values.items():
        if not value:
            continue
        text = str(value).strip()
        if not text:
            continue
        if target in text.lower():
            best_col = col
            best_snippet = _short_quote(text)
            break
    if best_col is None:
        for col, value in row_values.items():
            if value:
                best_col = col
                best_snippet = _short_quote(str(value))
                break
    return best_col, best_snippet
