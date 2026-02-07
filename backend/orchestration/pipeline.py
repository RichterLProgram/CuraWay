"""Linear orchestration of IDP, decisions, and regional aggregation."""

import json
from typing import Dict, List, Union

from pydantic import BaseModel

from aggregation.medical_desert_assessor import assess_medical_desert
from idp_agent import CapabilitySchema, IDPAgent, build_capability_decisions
from models.shared import FacilityWithCapabilityDecisions, RegionalAssessment


class PipelineResult(BaseModel):
    """Auditable container for each pipeline stage output."""

    raw_idp_output: List[Dict[str, object]]
    capability_decisions: Dict[str, Dict[str, dict]]
    regional_assessments: List[RegionalAssessment]


def run_pipeline(documents: List[str]) -> PipelineResult:
    """
    Run a linear, deterministic agent pipeline:
      1) IDP extraction
      2) Capability decision building
      3) Regional medical desert aggregation
    """
    idp_outputs: List[Union[CapabilitySchema, Dict[str, object]]] = []
    for doc in documents:
        # Handoff 1: IDP extraction. If the input is already an IDP payload,
        # use it directly for auditability; otherwise run the IDP agent with a
        # deterministic stub extractor (no LLM calls in this module).
        idp_payload = _try_parse_idp_payload(doc)
        if idp_payload is not None:
            idp_outputs.append(idp_payload)
        else:
            idp_agent = IDPAgent(llm_extractor=_deterministic_stub_extractor)
            idp_outputs.append(idp_agent.parse_facility_document(doc))

    # Handoff 2: Build auditable decisions from IDP outputs.
    capability_decisions: Dict[str, Dict[str, dict]] = {}
    facilities_for_aggregation: List[FacilityWithCapabilityDecisions] = []
    raw_idp_output: List[Dict[str, object]] = []

    for idx, output in enumerate(idp_outputs, start=1):
        facility_id = f"FAC-{idx:03d}"
        if isinstance(output, CapabilitySchema):
            facility_region = output.facility_info.region or "unknown"
            raw_idp_output.append(output.dict())
            decisions = build_capability_decisions(output)
        else:
            facility_region = (
                output.get("facility_info", {}).get("region") or "unknown"
            )
            raw_idp_output.append(output)
            decisions = build_capability_decisions(output)

        capability_decisions[facility_id] = {
            cap: decision.dict() for cap, decision in decisions.items()
        }

        facilities_for_aggregation.append(
            FacilityWithCapabilityDecisions(
                facility_id=facility_id,
                region=facility_region,
                capability_decisions=capability_decisions[facility_id],
            )
        )

    # Handoff 3: Regional aggregation based on finalized decisions.
    regional_assessments = assess_medical_desert(facilities_for_aggregation)

    return PipelineResult(
        raw_idp_output=raw_idp_output,
        capability_decisions=capability_decisions,
        regional_assessments=regional_assessments,
    )


def _try_parse_idp_payload(text: str) -> Union[Dict[str, object], None]:
    try:
        candidate = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(candidate, dict):
        return None
    if {"facility_info", "capabilities", "metadata"} <= set(candidate.keys()):
        return candidate
    return None


def _deterministic_stub_extractor(_: str) -> str:
    """
    Deterministic, LLM-free placeholder used to keep this module testable.
    Production deployments should replace this extractor upstream.
    """
    payload = {
        "facility_name": None,
        "country": None,
        "region": None,
        "capabilities": {
            "oncology_services": {"value": False, "confidence": 0.0, "evidence": []},
            "ct_scanner": {"value": False, "confidence": 0.0, "evidence": []},
            "mri_scanner": {"value": False, "confidence": 0.0, "evidence": []},
            "pathology_lab": {"value": False, "confidence": 0.0, "evidence": []},
            "genomic_testing": {"value": False, "confidence": 0.0, "evidence": []},
            "chemotherapy_delivery": {
                "value": False,
                "confidence": 0.0,
                "evidence": [],
            },
            "radiotherapy": {"value": False, "confidence": 0.0, "evidence": []},
            "icu": {"value": False, "confidence": 0.0, "evidence": []},
            "trial_coordinator": {"value": False, "confidence": 0.0, "evidence": []},
        },
        "suspicious_claims": [],
    }
    return json.dumps(payload)


if __name__ == "__main__":
    # Minimal runnable example using two pre-extracted IDP payloads.
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

    result = run_pipeline([doc_one, doc_two])
    # Example JSON output showing full pipeline output:
    print(json.dumps(result.dict(), indent=2))
