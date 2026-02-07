import json
import re
from collections import Counter, defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, root_validator, validator


class FacilityInfo(BaseModel):
    """Core facility identifiers extracted from text."""

    facility_name: str = Field(..., min_length=1)
    country: Optional[str] = None
    region: Optional[str] = None


class Capabilities(BaseModel):
    """Binary capability flags for a medical facility."""

    oncology_services: bool
    ct_scanner: bool
    mri_scanner: bool
    pathology_lab: bool
    genomic_testing: bool
    chemotherapy_delivery: bool
    radiotherapy: bool
    icu: bool
    trial_coordinator: bool


class Metadata(BaseModel):
    """Evidence and confidence metadata for each capability."""

    confidence_scores: Dict[str, float]
    extracted_evidence: Dict[str, List[str]]
    suspicious_claims: List[str]

    @validator("confidence_scores")
    def validate_confidences(cls, value: Dict[str, float]) -> Dict[str, float]:
        for key, score in value.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"Confidence score for {key} out of range: {score}")
        return value


class CapabilitySchema(BaseModel):
    """Validated output schema for the IDP agent."""

    facility_info: FacilityInfo
    capabilities: Capabilities
    metadata: Metadata

    @root_validator
    def validate_alignment(cls, values: Dict) -> Dict:
        capabilities = values.get("capabilities")
        metadata = values.get("metadata")
        if not capabilities or not metadata:
            return values
        capability_keys = set(capabilities.dict().keys())
        confidence_keys = set(metadata.confidence_scores.keys())
        evidence_keys = set(metadata.extracted_evidence.keys())
        if capability_keys != confidence_keys:
            raise ValueError("confidence_scores keys must match capability keys")
        if capability_keys != evidence_keys:
            raise ValueError("extracted_evidence keys must match capability keys")
        return values


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
        """
        Args:
            llm_extractor: Callable that takes a prompt string and returns JSON.
            chunk_size: Max characters per chunk.
            chunk_overlap: Character overlap between adjacent chunks.
            accept_threshold: Minimum confidence to accept a True capability.
            weak_confidence_cap: Cap for confidence when evidence is weak.
        """
        self.llm_extractor = llm_extractor
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.accept_threshold = accept_threshold
        self.weak_confidence_cap = weak_confidence_cap

    def parse_facility_document(self, text: str) -> CapabilitySchema:
        """
        Parse a single facility document and return a validated schema.

        Pipeline:
          1) Chunk input text
          2) Prompt LLM to extract structured signals
          3) Aggregate signals across chunks
          4) Assign conservative confidence scores
          5) Detect suspicious claims
        """
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
        data = json.loads(raw)
        return data

    def _build_prompt(self, chunk: str) -> str:
        return (
            "You are an information extraction engine. "
            "Return ONLY strict JSON and nothing else.\n\n"
            "Extract facility info and capability signals from the text below. "
            "Do NOT infer; only extract explicit evidence. "
            "Each capability must include evidence snippets and a confidence score.\n\n"
            "JSON schema:\n"
            "{\n"
            '  "facility_name": "string or null",\n'
            '  "country": "string or null",\n'
            '  "region": "string or null",\n'
            '  "capabilities": {\n'
            '    "oncology_services": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "ct_scanner": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "mri_scanner": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "pathology_lab": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "genomic_testing": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "chemotherapy_delivery": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "radiotherapy": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "icu": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]},\n'
            '    "trial_coordinator": {"value": true|false, "confidence": 0-1, "evidence": ["snippet"]}\n'
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
        capability_keys = list(Capabilities.__fields__.keys())
        evidence: Dict[str, List[str]] = {key: [] for key in capability_keys}
        confidences: Dict[str, float] = {key: 0.0 for key in capability_keys}
        decisions: Dict[str, bool] = {key: False for key in capability_keys}

        for result in results:
            cap_block = result.get("capabilities", {})
            for key in capability_keys:
                cap = cap_block.get(key, {})
                cap_value = bool(cap.get("value", False))
                cap_conf = float(cap.get("confidence", 0.0) or 0.0)
                cap_evidence = [e for e in cap.get("evidence", []) if e]
                if cap_evidence:
                    evidence[key].extend(cap_evidence)
                    confidences[key] = max(confidences[key], cap_conf)
                if cap_value and cap_evidence and cap_conf >= self.accept_threshold:
                    decisions[key] = True

        for key in capability_keys:
            evidence[key] = self._dedupe_snippets(evidence[key])
            if decisions[key]:
                confidences[key] = max(confidences[key], self.accept_threshold)
            else:
                if evidence[key]:
                    confidences[key] = min(confidences[key], self.weak_confidence_cap)
                else:
                    confidences[key] = 0.05

        suspicious_claims = self._detect_suspicious_claims(full_text)
        for result in results:
            suspicious_claims.extend(result.get("suspicious_claims", []))
        suspicious_claims = self._dedupe_snippets(suspicious_claims)

        capabilities = Capabilities(**decisions)
        metadata = Metadata(
            confidence_scores=confidences,
            extracted_evidence=evidence,
            suspicious_claims=suspicious_claims,
        )
        return capabilities, metadata

    def _detect_suspicious_claims(self, text: str) -> List[str]:
        phrases = [
            "world-class",
            "state-of-the-art",
            "fully equipped oncology center",
            "advanced diagnostics",
            "research-ready hospital",
            "cutting-edge",
            "best-in-class",
        ]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        suspicious = []
        for sentence in sentences:
            lower = sentence.lower()
            if any(phrase in lower for phrase in phrases):
                suspicious.append(sentence.strip())
        return [s for s in suspicious if s]

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


if __name__ == "__main__":
    sample_text = (
        "Sunrise Medical Center is a regional hospital in Kintampo, Ghana.\n"
        "Our facility includes a 16-slice CT scanner and a dedicated ICU with 8 beds.\n"
        "We provide chemotherapy delivery for solid tumors and have a pathology lab.\n"
        "World-class care for all patients.\n"
        "No radiotherapy services are listed.\n"
    )

    def mock_llm(prompt: str) -> str:
        text = prompt.split("TEXT:\n", 1)[-1]
        payload = {
            "facility_name": "Sunrise Medical Center" if "Sunrise" in text else None,
            "country": "Ghana" if "Ghana" in text else None,
            "region": "Kintampo" if "Kintampo" in text else None,
            "capabilities": {
                "oncology_services": {
                    "value": "chemotherapy" in text.lower(),
                    "confidence": 0.7 if "chemotherapy" in text.lower() else 0.0,
                    "evidence": [
                        "We provide chemotherapy delivery for solid tumors"
                    ]
                    if "chemotherapy" in text.lower()
                    else [],
                },
                "ct_scanner": {
                    "value": "ct scanner" in text.lower(),
                    "confidence": 0.8 if "ct scanner" in text.lower() else 0.0,
                    "evidence": ["includes a 16-slice CT scanner"]
                    if "ct scanner" in text.lower()
                    else [],
                },
                "mri_scanner": {"value": False, "confidence": 0.0, "evidence": []},
                "pathology_lab": {
                    "value": "pathology lab" in text.lower(),
                    "confidence": 0.75 if "pathology lab" in text.lower() else 0.0,
                    "evidence": ["have a pathology lab"]
                    if "pathology lab" in text.lower()
                    else [],
                },
                "genomic_testing": {"value": False, "confidence": 0.0, "evidence": []},
                "chemotherapy_delivery": {
                    "value": "chemotherapy" in text.lower(),
                    "confidence": 0.7 if "chemotherapy" in text.lower() else 0.0,
                    "evidence": [
                        "We provide chemotherapy delivery for solid tumors"
                    ]
                    if "chemotherapy" in text.lower()
                    else [],
                },
                "radiotherapy": {"value": False, "confidence": 0.0, "evidence": []},
                "icu": {
                    "value": "icu" in text.lower(),
                    "confidence": 0.8 if "icu" in text.lower() else 0.0,
                    "evidence": ["dedicated ICU with 8 beds"]
                    if "icu" in text.lower()
                    else [],
                },
                "trial_coordinator": {
                    "value": False,
                    "confidence": 0.0,
                    "evidence": [],
                },
            },
            "suspicious_claims": [
                "World-class care for all patients."
            ]
            if "world-class" in text.lower()
            else [],
        }
        return json.dumps(payload)

    agent = IDPAgent(llm_extractor=mock_llm)
    parsed = agent.parse_facility_document(sample_text)
    print(parsed.json(indent=2))
