from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.ontology.normalize import load_ontology, normalize_capability_name
from src.observability.tracing import trace_event


class FacilityAnswerRequest(BaseModel):
    facility_id: str
    required_capability_codes: List[str] = Field(default_factory=list)
    question: Optional[str] = None
    min_threshold: float = Field(default=1.0, ge=0, le=1)
    include_evidence: bool = True
    facility: Optional[Dict[str, Any]] = None
    supply: Optional[List[Dict[str, Any]]] = None


class FacilityAnswerResponse(BaseModel):
    trace_id: str
    answer: Literal["yes", "no", "partial"]
    coverage_score: float = Field(ge=0, le=1)
    present: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    validator_verdict: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    evidence_citation_ids: List[str] = Field(default_factory=list)
    explanation: str


def answer_facility(
    payload: Dict[str, Any],
    trace_id: str,
) -> Dict[str, Any]:
    request = FacilityAnswerRequest.model_validate(payload)
    facility = _resolve_facility(request)
    required = _resolve_required_codes(request)

    present_codes = _extract_codes(facility)
    present = sorted([code for code in required if code in present_codes])
    missing = sorted([code for code in required if code not in present_codes])

    coverage_score = 0.0
    if required:
        coverage_score = len(present) / len(required)

    validator_verdict = (facility.get("validation", {}) or {}).get("verdict")
    confidence = _confidence_from_verdict(coverage_score, validator_verdict)

    answer = "no"
    if validator_verdict == "impossible":
        answer = "no"
    elif coverage_score >= request.min_threshold and not missing:
        answer = "yes"
    elif coverage_score > 0:
        answer = "partial"

    evidence_ids = []
    if request.include_evidence:
        evidence_ids = _collect_citation_ids(facility, present)

    explanation = _build_explanation(answer, present, missing, validator_verdict)

    trace_event(
        trace_id,
        "facility_answer",
        inputs_ref={"facility_id": request.facility_id, "required_codes": required},
        outputs_ref={"answer": answer, "coverage_score": round(coverage_score, 3)},
    )

    response = FacilityAnswerResponse(
        trace_id=trace_id,
        answer=answer,
        coverage_score=round(coverage_score, 3),
        present=present,
        missing=missing,
        validator_verdict=validator_verdict,
        confidence=round(confidence, 3),
        evidence_citation_ids=evidence_ids[:30],
        explanation=explanation,
    )
    return response.model_dump()


def _resolve_facility(request: FacilityAnswerRequest) -> Dict[str, Any]:
    if request.facility:
        return request.facility
    if request.supply:
        for item in request.supply:
            if item.get("facility_id") == request.facility_id:
                return item
    return {"facility_id": request.facility_id, "capabilities": []}


def _resolve_required_codes(request: FacilityAnswerRequest) -> List[str]:
    if request.required_capability_codes:
        return _normalize_codes(request.required_capability_codes)
    if request.question:
        return _codes_from_question(request.question)
    return []


def _normalize_codes(codes: List[str]) -> List[str]:
    return sorted({code.strip() for code in codes if isinstance(code, str) and code.strip()})


def _codes_from_question(question: str) -> List[str]:
    question_lower = question.lower()
    ontology = load_ontology()
    found: List[str] = []
    for code, info in (ontology.get("capabilities") or {}).items():
        synonyms = [info.get("display_name", code)] + list(info.get("synonyms", []))
        if any(str(syn).lower() in question_lower for syn in synonyms if syn):
            found.append(code)
    return _normalize_codes(found)


def _extract_codes(facility: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    for code in facility.get("canonical_capabilities") or []:
        if code not in codes:
            codes.append(code)
    for entry in facility.get("capabilities", []):
        if isinstance(entry, dict) and entry.get("capability_code"):
            code = entry.get("capability_code")
            if code not in codes:
                codes.append(code)
            continue
        normalized = normalize_capability_name(str(entry))
        code = normalized.get("code")
        if code and code not in codes:
            codes.append(code)
    return codes


def _collect_citation_ids(facility: Dict[str, Any], present: List[str]) -> List[str]:
    citation_ids: List[str] = []
    for entry in facility.get("capabilities", []):
        if isinstance(entry, dict) and entry.get("capability_code") in present:
            citation_ids.extend(entry.get("citation_ids") or [])
    return list(dict.fromkeys([cid for cid in citation_ids if cid]))


def _confidence_from_verdict(coverage: float, verdict: Optional[str]) -> float:
    base = coverage
    if verdict == "impossible":
        return max(0.1, base * 0.3)
    if verdict == "suspicious":
        return max(0.2, base * 0.7)
    return min(1.0, max(0.3, base))


def _build_explanation(
    answer: str,
    present: List[str],
    missing: List[str],
    verdict: Optional[str],
) -> str:
    if verdict == "impossible":
        return "Validator flagged the facility as impossible for the requested capabilities."
    if answer == "yes":
        return "Facility meets all required capabilities."
    if answer == "partial":
        return f"Facility covers {len(present)} of {len(present) + len(missing)} required capabilities."
    return "Facility does not meet the requested capabilities."
