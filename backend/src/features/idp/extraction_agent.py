"""LLM / NLP / OCR – Intelligent Document Parsing agent."""

import json
import re
from collections import Counter
from typing import Callable, Dict, List, Optional, Tuple

from features.idp.schemas import Capabilities, CapabilitySchema, FacilityInfo, Metadata
from features.validation.anomaly_validator import detect_suspicious_claims


class IDPAgent:
    """
    Intelligent Document Parsing (IDP) agent for extracting
    facility capabilities from unstructured text.
    """

    def __init__(
        self,
        llm_extractor: Callable[[str], str],
        chunk_size: int = 1800,
        chunk_overlap: int = 200,
        accept_threshold: float = 0.6,
        weak_confidence_cap: float = 0.4,
    ) -> None:
        self.llm_extractor = llm_extractor
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.accept_threshold = accept_threshold
        self.weak_confidence_cap = weak_confidence_cap

    def parse_facility_document(self, text: str) -> CapabilitySchema:
        chunks = self._chunk_text(text)
        chunk_results = [self._extract_from_chunk(chunk) for chunk in chunks]
        facility_info = self._aggregate_facility_info(chunk_results)
        capabilities, metadata = self._aggregate_capabilities(chunk_results, text)
        return CapabilitySchema(
            facility_info=facility_info,
            capabilities=capabilities,
            metadata=metadata,
        )

    def _chunk_text(self, text: str) -> List[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: List[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) + 1 <= self.chunk_size:
                current = f"{current}\n{paragraph}".strip()
                continue
            if current:
                chunks.append(current)
            current = paragraph
        if current:
            chunks.append(current)
        if not chunks:
            return [text[: self.chunk_size]]
        if self.chunk_overlap <= 0 or len(chunks) == 1:
            return chunks
        overlapped = []
        for idx, chunk in enumerate(chunks):
            if idx == 0:
                overlapped.append(chunk)
                continue
            prev = chunks[idx - 1]
            overlap = prev[-self.chunk_overlap :]
            overlapped.append(f"{overlap}\n{chunk}".strip())
        return overlapped

    def _extract_from_chunk(self, chunk: str) -> Dict:
        prompt = self._build_prompt(chunk)
        raw = self.llm_extractor(prompt)
        return json.loads(raw)

    def _build_prompt(self, chunk: str) -> str:
        return (
            "You are an information extraction engine. "
            "Return ONLY strict JSON and nothing else.\n\n"
            "Extract facility info and capability signals from the text below. "
            "Do NOT infer; only extract explicit evidence. "
            "Each capability must include evidence snippets and a confidence score.\n"
            "If line numbers are present (L0001|...), include them in evidence text.\n"
            "Prefer evidence objects with document_id and chunk_id (line-based).\n\n"
            "JSON schema:\n"
            "{\n"
            '  "facility_name": "string or null",\n'
            '  "country": "string or null",\n'
            '  "region": "string or null",\n'
            '  "capabilities": {\n'
            '    "oncology_services": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "ct_scanner": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "mri_scanner": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "pathology_lab": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "genomic_testing": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "chemotherapy_delivery": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "radiotherapy": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "icu": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]},\n'
            '    "trial_coordinator": {"value": true|false, "confidence": 0-1, "evidence": ["snippet" or {"text": "...", "document_id": "...", "chunk_id": "..."}]}\n'
            "  },\n"
            '  "suspicious_claims": ["claim"]\n'
            "}\n\n"
            "Rules:\n"
            "- No free text explanations.\n"
            "- Use empty arrays when no evidence.\n"
            "- Only set value=true when evidence is explicit in the text.\n\n"
            f"TEXT:\n{chunk}"
        )

    def _aggregate_facility_info(self, results: List[Dict]) -> FacilityInfo:
        names = [r.get("facility_name") for r in results if r.get("facility_name")]
        countries = [r.get("country") for r in results if r.get("country")]
        regions = [r.get("region") for r in results if r.get("region")]
        facility_name = self._most_common_non_empty(names) or "Unknown Facility"
        return FacilityInfo(
            facility_name=facility_name,
            country=self._most_common_non_empty(countries),
            region=self._most_common_non_empty(regions),
        )

    def _aggregate_capabilities(
        self, results: List[Dict], full_text: str
    ) -> Tuple[Capabilities, Metadata]:
        capability_keys = list(Capabilities.model_fields.keys())
        evidence: Dict[str, List[object]] = {key: [] for key in capability_keys}
        confidences: Dict[str, float] = {key: 0.0 for key in capability_keys}
        decisions: Dict[str, bool] = {key: False for key in capability_keys}
        document_id = self._extract_document_id(full_text)

        for result in results:
            cap_block = result.get("capabilities", {})
            for key in capability_keys:
                cap = cap_block.get(key, {})
                cap_value = bool(cap.get("value", False))
                cap_conf = float(cap.get("confidence", 0.0) or 0.0)
                cap_evidence = [e for e in cap.get("evidence", []) if e]
                if cap_evidence:
                    normalized = [
                        self._normalize_evidence_item(item, document_id)
                        for item in cap_evidence
                        if item
                    ]
                    evidence[key].extend([item for item in normalized if item])
                    confidences[key] = max(confidences[key], cap_conf)
                if cap_value and cap_evidence and cap_conf >= self.accept_threshold:
                    decisions[key] = True

        for key in capability_keys:
            evidence[key] = self._dedupe_evidence_items(evidence[key])
            if decisions[key]:
                confidences[key] = max(confidences[key], self.accept_threshold)
            else:
                if evidence[key]:
                    confidences[key] = min(confidences[key], self.weak_confidence_cap)
                else:
                    confidences[key] = 0.05

        suspicious_claims = detect_suspicious_claims(full_text)
        for result in results:
            suspicious_claims.extend(result.get("suspicious_claims", []))
        suspicious_claims = self._dedupe_snippets(suspicious_claims)

        return (
            Capabilities(**decisions),
            Metadata(
                confidence_scores=confidences,
                extracted_evidence=evidence,
                suspicious_claims=suspicious_claims,
            ),
        )

    def _most_common_non_empty(self, values: List[Optional[str]]) -> Optional[str]:
        cleaned = [v.strip() for v in values if v and v.strip()]
        if not cleaned:
            return None
        counts = Counter(cleaned)
        return counts.most_common(1)[0][0]

    def _dedupe_snippets(self, snippets: List[str]) -> List[str]:
        seen = set()
        deduped = []
        for snippet in snippets:
            norm = re.sub(r"\s+", " ", snippet.strip())
            if not norm or norm in seen:
                continue
            seen.add(norm)
            deduped.append(norm)
        return deduped

    def _dedupe_evidence_items(self, items: List[object]) -> List[object]:
        seen = set()
        deduped: List[object] = []
        for item in items:
            if isinstance(item, dict):
                text = re.sub(r"\s+", " ", str(item.get("text", "")).strip())
                doc_id = str(item.get("document_id", "")).strip()
                chunk_id = str(item.get("chunk_id", "")).strip()
                key = (text, doc_id, chunk_id)
                if not text or key in seen:
                    continue
                seen.add(key)
                deduped.append({"text": text, "document_id": doc_id, "chunk_id": chunk_id})
            else:
                text = re.sub(r"\s+", " ", str(item).strip())
                if not text or text in seen:
                    continue
                seen.add(text)
                deduped.append(text)
        return deduped

    def _normalize_evidence_item(self, item: object, document_id: str) -> object:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            doc_id = str(item.get("document_id", "") or document_id).strip()
            chunk_id = str(item.get("chunk_id", "")).strip()
            if not chunk_id:
                chunk_id = self._infer_line_chunk(text)
            return {"text": text, "document_id": doc_id or "unknown", "chunk_id": chunk_id or "unknown"}
        text = str(item).strip()
        if not text:
            return None
        chunk_id = self._infer_line_chunk(text)
        return {"text": text, "document_id": document_id or "unknown", "chunk_id": chunk_id or "unknown"}

    def _extract_document_id(self, text: str) -> str:
        for line in text.splitlines()[:3]:
            if line.startswith("DOCUMENT_ID:"):
                return line.split("DOCUMENT_ID:", 1)[-1].strip()
        return "unknown"

    def _infer_line_chunk(self, text: str) -> str:
        match = re.match(r"^L(\d+)\|", text)
        if match:
            return f"line-{match.group(1)}"
        return "unknown"
