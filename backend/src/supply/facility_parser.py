from __future__ import annotations

from src.ai.llm_extractors import extract_facility_capabilities
from src.ontology.normalize import normalize_supply
from src.shared.models import FacilityCapabilities
from src.supply.citations import attach_text_citations


def parse_facility_document(
    text: str,
    source_doc_id: str | None = None,
    trace_id: str | None = None,
) -> FacilityCapabilities:
    """
    Parse unstructured facility text into structured capabilities using the LLM gateway.
    """
    result = extract_facility_capabilities(
        text,
        trace_id=trace_id,
        input_refs={
            "source_doc_id": source_doc_id or "facility_document",
            "text_length": len(text),
        },
    )
    doc_id = source_doc_id or "facility_document"
    result = attach_text_citations(
        result, text, doc_id, source_type="text", chunk_id="chunk_0"
    )
    return normalize_supply(result, source_text=text)
