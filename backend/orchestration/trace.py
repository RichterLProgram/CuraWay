"""Deterministic, step-level trace builder for pipeline auditability."""

import json
from typing import Dict, List

from pydantic import BaseModel
from typing_extensions import Literal

from orchestration.pipeline import PipelineResult, run_pipeline


class TraceEvidenceSnippet(BaseModel):
    """Evidence snippet with provenance for audit trails."""

    text: str
    document_id: str
    chunk_id: str


class CapabilityDecisionTrace(BaseModel):
    """Decision trace for a single capability in a facility."""

    facility_id: str
    capability: str
    value: bool
    confidence: float
    decision_reason: str
    evidence: List[TraceEvidenceSnippet]
    rationale: str


class RegionalAssessmentTrace(BaseModel):
    """Regional decision trace for medical desert classification."""

    region: str
    risk_level: str
    coverage_score: float
    facility_ids: List[str]
    confirmed_capabilities: List[str]
    missing_capabilities: List[str]
    rationale: str


class TraceStep(BaseModel):
    """Step-level trace with inputs, outputs, and rationale."""

    step_name: Literal[
        "idp_extraction",
        "capability_decisions",
        "medical_desert_assessment",
    ]
    input_summary: Dict[str, object]
    output_summary: Dict[str, object]
    decision_details: List[Dict[str, object]]


class PipelineTrace(BaseModel):
    """Full pipeline trace suitable for audits and jury review."""

    steps: List[TraceStep]


def build_pipeline_trace(pipeline_result: PipelineResult) -> PipelineTrace:
    """
    Build a deterministic, LLM-free audit trace for each pipeline step.

    The trace references the data that was used and the reasons for
    decision outputs at each stage.
    """
    steps: List[TraceStep] = []

    # Step 1: IDP extraction trace. We only have raw IDP outputs here,
    # so we summarize what was produced rather than the original documents.
    idp_outputs = pipeline_result.raw_idp_output
    facility_infos = [
        output.get("facility_info", {}) for output in idp_outputs if isinstance(output, dict)
    ]
    steps.append(
        TraceStep(
            step_name="idp_extraction",
            input_summary={
                "source": "documents",
                "document_count": len(idp_outputs),
                "note": "documents not stored in PipelineResult; count inferred from IDP outputs",
            },
            output_summary={
                "idp_records": len(idp_outputs),
                "facility_info_samples": facility_infos[:3],
            },
            decision_details=[],
        )
    )

    # Step 2: Capability decision trace. We explain each decision using
    # the decision_reason and evidence snippets already produced.
    decision_traces: List[CapabilityDecisionTrace] = []
    for facility_id, decisions in pipeline_result.capability_decisions.items():
        for capability, decision in decisions.items():
            evidence = _normalize_evidence(decision.get("evidence", []))
            reason = decision.get("decision_reason", "insufficient_evidence")
            rationale = _rationale_for_decision(reason, decision.get("confidence", 0.0), evidence)
            decision_traces.append(
                CapabilityDecisionTrace(
                    facility_id=facility_id,
                    capability=capability,
                    value=bool(decision.get("value", False)),
                    confidence=float(decision.get("confidence", 0.0)),
                    decision_reason=reason,
                    evidence=evidence,
                    rationale=rationale,
                )
            )

    steps.append(
        TraceStep(
            step_name="capability_decisions",
            input_summary={
                "source": "raw_idp_output",
                "facility_count": len(pipeline_result.capability_decisions),
            },
            output_summary={
                "decision_count": len(decision_traces),
                "facility_ids": list(pipeline_result.capability_decisions.keys()),
            },
            decision_details=[trace.dict() for trace in decision_traces],
        )
    )

    # Step 3: Medical desert assessment trace. We derive the regional reasoning
    # deterministically from the facility-level decisions.
    regional_traces: List[RegionalAssessmentTrace] = []
    essential_capabilities = [
        "oncology_services",
        "ct_scanner",
        "mri_scanner",
        "pathology_lab",
        "chemotherapy_delivery",
        "icu",
    ]

    for assessment in pipeline_result.regional_assessments:
        facility_ids = assessment.facility_ids
        confirmed: List[str] = []
        missing: List[str] = []
        for capability in essential_capabilities:
            if _region_has_capability(
                pipeline_result.capability_decisions, facility_ids, capability
            ):
                confirmed.append(capability)
            else:
                missing.append(capability)

        rationale = (
            f"Confirmed {len(confirmed)}/{len(essential_capabilities)} essential capabilities "
            f"across facilities {facility_ids}. Missing: {missing}."
        )
        regional_traces.append(
            RegionalAssessmentTrace(
                region=assessment.region,
                risk_level=assessment.risk_level.level,
                coverage_score=assessment.coverage_score,
                facility_ids=facility_ids,
                confirmed_capabilities=confirmed,
                missing_capabilities=missing,
                rationale=rationale,
            )
        )

    steps.append(
        TraceStep(
            step_name="medical_desert_assessment",
            input_summary={
                "source": "capability_decisions",
                "regions": [a.region for a in pipeline_result.regional_assessments],
            },
            output_summary={
                "assessment_count": len(regional_traces),
            },
            decision_details=[trace.dict() for trace in regional_traces],
        )
    )

    return PipelineTrace(steps=steps)


def _normalize_evidence(raw_evidence: List[object]) -> List[TraceEvidenceSnippet]:
    evidence: List[TraceEvidenceSnippet] = []
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
                TraceEvidenceSnippet(
                    text=text,
                    document_id=document_id,
                    chunk_id=chunk_id,
                )
            )
    return evidence


def _rationale_for_decision(
    decision_reason: str, confidence: float, evidence: List[TraceEvidenceSnippet]
) -> str:
    if decision_reason == "direct_evidence":
        return (
            "Capability confirmed due to direct evidence snippets with sufficient confidence."
        )
    if decision_reason == "conflicting_evidence":
        return "Capability marked false due to conflicting positive and negative evidence."
    if decision_reason == "suspicious_claim":
        return "Capability marked false due to suspicious claim without strong evidence."
    if evidence:
        return (
            "Evidence exists but confidence is below conservative acceptance threshold."
        )
    return f"No explicit evidence; confidence recorded as {confidence}."


def _region_has_capability(
    decisions: Dict[str, Dict[str, dict]],
    facility_ids: List[str],
    capability: str,
) -> bool:
    for facility_id in facility_ids:
        facility_decisions = decisions.get(facility_id, {})
        decision = facility_decisions.get(capability, {})
        if decision.get("value") is True and decision.get("decision_reason") == "direct_evidence":
            return True
    return False


if __name__ == "__main__":
    # Minimal runnable example using the pipeline and trace builder.
    doc_one = json.dumps(
        {
            "facility_info": {"facility_name": "North Clinic", "country": "GH", "region": "North"},
            "capabilities": {
                "oncology_services": True,
                "ct_scanner": True,
                "mri_scanner": False,
                "pathology_lab": True,
                "genomic_testing": False,
                "chemotherapy_delivery": False,
                "radiotherapy": False,
                "icu": True,
                "trial_coordinator": False,
            },
            "metadata": {
                "confidence_scores": {
                    "oncology_services": 0.65,
                    "ct_scanner": 0.8,
                    "mri_scanner": 0.0,
                    "pathology_lab": 0.7,
                    "genomic_testing": 0.0,
                    "chemotherapy_delivery": 0.3,
                    "radiotherapy": 0.0,
                    "icu": 0.75,
                    "trial_coordinator": 0.0,
                },
                "extracted_evidence": {
                    "oncology_services": ["oncology clinic onsite"],
                    "ct_scanner": ["16-slice CT scanner"],
                    "mri_scanner": [],
                    "pathology_lab": ["pathology lab available"],
                    "genomic_testing": [],
                    "chemotherapy_delivery": [],
                    "radiotherapy": [],
                    "icu": ["ICU with 6 beds"],
                    "trial_coordinator": [],
                },
                "suspicious_claims": [],
            },
        }
    )

    doc_two = json.dumps(
        {
            "facility_info": {"facility_name": "South Clinic", "country": "GH", "region": "South"},
            "capabilities": {
                "oncology_services": False,
                "ct_scanner": False,
                "mri_scanner": False,
                "pathology_lab": False,
                "genomic_testing": False,
                "chemotherapy_delivery": False,
                "radiotherapy": False,
                "icu": False,
                "trial_coordinator": False,
            },
            "metadata": {
                "confidence_scores": {
                    "oncology_services": 0.2,
                    "ct_scanner": 0.0,
                    "mri_scanner": 0.0,
                    "pathology_lab": 0.0,
                    "genomic_testing": 0.0,
                    "chemotherapy_delivery": 0.0,
                    "radiotherapy": 0.0,
                    "icu": 0.0,
                    "trial_coordinator": 0.0,
                },
                "extracted_evidence": {
                    "oncology_services": [],
                    "ct_scanner": [],
                    "mri_scanner": [],
                    "pathology_lab": [],
                    "genomic_testing": [],
                    "chemotherapy_delivery": [],
                    "radiotherapy": [],
                    "icu": [],
                    "trial_coordinator": [],
                },
                "suspicious_claims": ["world-class cancer center"],
            },
        }
    )

    pipeline_result = run_pipeline([doc_one, doc_two])
    trace = build_pipeline_trace(pipeline_result)
    # Example JSON output showing full pipeline trace:
    print(json.dumps(trace.dict(), indent=2))
