"""Deterministische Entscheidung + Why – auditable capability decisions."""

from typing import Dict, List, Union

from pydantic import BaseModel
from typing_extensions import Literal

from features.idp.schemas import CapabilitySchema, EvidenceSnippet
from features.validation.anomaly_validator import is_negated, suspicious_for_capability


class CapabilityDecision(BaseModel):
    """Jury-facing decision record for a single capability."""

    value: bool
    confidence: float
    decision_reason: Literal[
        "direct_evidence",
        "insufficient_evidence",
        "conflicting_evidence",
        "suspicious_claim",
    ]
    evidence: List[EvidenceSnippet]


def build_capability_decisions(
    idp_output: Union[CapabilitySchema, Dict[str, object]],
) -> Dict[str, CapabilityDecision]:
    """
    Convert raw IDP outputs into auditable capability decisions.

    This layer is deterministic, conservative, and favors underclaiming.
    """
    if isinstance(idp_output, CapabilitySchema):
        capabilities = idp_output.capabilities.model_dump()
        confidences = idp_output.metadata.confidence_scores
        evidence_map = idp_output.metadata.extracted_evidence
        suspicious_claims = idp_output.metadata.suspicious_claims
    else:
        capabilities = idp_output["capabilities"]
        confidences = idp_output["metadata"]["confidence_scores"]
        evidence_map = idp_output["metadata"]["extracted_evidence"]
        suspicious_claims = idp_output["metadata"]["suspicious_claims"]

    decisions: Dict[str, CapabilityDecision] = {}
    strong_threshold = 0.6
    suspicious_override_threshold = 0.8

    for capability, raw_value in capabilities.items():
        confidence = float(confidences.get(capability, 0.0))
        raw_evidence = evidence_map.get(capability, [])
        evidence = _normalize_evidence(raw_evidence)

        has_negation = any(is_negated(ev.text) for ev in evidence)
        has_positive = any(not is_negated(ev.text) for ev in evidence)
        has_conflict = has_negation and has_positive

        suspicious_match = suspicious_for_capability(capability, suspicious_claims)

        if raw_value and confidence >= strong_threshold and evidence and not has_conflict:
            value = True
            reason = "direct_evidence"
        else:
            value = False
            reason = "insufficient_evidence"

        if has_conflict:
            value = False
            reason = "conflicting_evidence"

        if suspicious_match and confidence < suspicious_override_threshold:
            value = False
            reason = "suspicious_claim"

        decisions[capability] = CapabilityDecision(
            value=value,
            confidence=confidence,
            decision_reason=reason,
            evidence=evidence,
        )

    return decisions


def _normalize_evidence(raw_evidence: List[object]) -> List[EvidenceSnippet]:
    evidence: List[EvidenceSnippet] = []
    for item in raw_evidence:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            document_id = str(item.get("document_id", "unknown")).strip() or "unknown"
            chunk_id = str(item.get("chunk_id", "unknown")).strip() or "unknown"
        else:
            text = str(item).strip()
            document_id = "unknown"
            chunk_id = "unknown"
        if text:
            evidence.append(
                EvidenceSnippet(
                    text=text,
                    document_id=document_id,
                    chunk_id=chunk_id,
                )
            )
    return evidence
