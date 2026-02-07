"""Linear orchestration of IDP, decisions, and regional aggregation."""

import json
from typing import Callable, Dict, List, Union

from pydantic import BaseModel

from features.aggregation.medical_desert_assessor import assess_medical_desert
from features.decision.capability_decision import build_capability_decisions
from features.idp.extraction_agent import IDPAgent
from features.idp.llm_extractors import load_llm_extractor
from features.idp.schemas import CapabilitySchema
from features.models.shared import FacilityWithCapabilityDecisions, RegionalAssessment


class PipelineResult(BaseModel):
    """Auditable container for each pipeline stage output."""

    raw_idp_output: List[Dict[str, object]]
    capability_decisions: Dict[str, Dict[str, dict]]
    regional_assessments: List[RegionalAssessment]


def run_pipeline(
    documents: List[str],
    llm_extractor: Callable[[str], str],
) -> PipelineResult:
    """
    Run a linear, deterministic agent pipeline:
      1) IDP extraction (always uses real IDP agent for raw text)
      2) Capability decision building
      3) Regional medical desert aggregation

    For raw text, llm_extractor is required and the IDP agent runs explicitly.
    For pre-extracted JSON, the payload must already contain document_id and
    chunk_id in evidence items.
    """
    idp_outputs: List[Union[CapabilitySchema, Dict[str, object]]] = []
    for doc in documents:
        idp_payload = _try_parse_idp_payload(doc)
        if idp_payload is not None:
            _validate_pre_extracted_provenance(idp_payload)
            idp_outputs.append(idp_payload)
        else:
            idp_agent = IDPAgent(llm_extractor=llm_extractor)
            idp_outputs.append(idp_agent.parse_facility_document(doc))

    # Handoff 2: Build auditable decisions from IDP outputs.
    capability_decisions: Dict[str, Dict[str, dict]] = {}
    facilities_for_aggregation: List[FacilityWithCapabilityDecisions] = []
    raw_idp_output: List[Dict[str, object]] = []

    for idx, output in enumerate(idp_outputs, start=1):
        facility_id = f"FAC-{idx:03d}"
        doc_id = f"DOC-{idx:03d}"
        if isinstance(output, CapabilitySchema):
            facility_region = output.facility_info.region or "unknown"
            raw_idp_output.append(output.model_dump())
            decisions = build_capability_decisions(output)
        else:
            facility_region = (
                output.get("facility_info", {}).get("region") or "unknown"
            )
            raw_idp_output.append(output)
            decisions = build_capability_decisions(output)

        decisions_with_provenance = _enrich_decisions_with_provenance(
            decisions, doc_id
        )
        capability_decisions[facility_id] = decisions_with_provenance

        facilities_for_aggregation.append(
            FacilityWithCapabilityDecisions(
                facility_id=facility_id,
                region=facility_region,
                capability_decisions=decisions_with_provenance,
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


def _validate_pre_extracted_provenance(payload: Dict[str, object]) -> None:
    """Require document_id and chunk_id in evidence for pre-extracted JSON."""
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return
    evidence_map = metadata.get("extracted_evidence")
    if not isinstance(evidence_map, dict):
        return
    for cap, items in evidence_map.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                doc_id = item.get("document_id")
                chunk_id = item.get("chunk_id")
                if not doc_id or str(doc_id).strip() in ("", "unknown"):
                    raise ValueError(
                        f"Pre-extracted evidence for {cap} missing document_id; "
                        "audit-grade provenance required."
                    )
                if not chunk_id or str(chunk_id).strip() in ("", "unknown"):
                    raise ValueError(
                        f"Pre-extracted evidence for {cap} missing chunk_id; "
                        "audit-grade provenance required."
                    )
            elif item and str(item).strip():
                raise ValueError(
                    f"Pre-extracted evidence for {cap} must be dicts with "
                    "document_id and chunk_id, not plain strings."
                )


def _enrich_decisions_with_provenance(
    decisions: Dict[str, object], document_id: str
) -> Dict[str, dict]:
    """Enrich evidence with document_id and chunk_id when missing."""
    enriched: Dict[str, dict] = {}
    for cap, decision in decisions.items():
        d = decision.model_dump() if hasattr(decision, "model_dump") else dict(decision)
        evidence = d.get("evidence", [])
        enriched_evidence = []
        for ev in evidence:
            ev_dict = dict(ev) if not isinstance(ev, dict) else ev
            doc_id_val = str(ev_dict.get("document_id") or "unknown").strip()
            chunk_id_val = str(ev_dict.get("chunk_id") or "unknown").strip()
            if doc_id_val in ("", "unknown"):
                ev_dict["document_id"] = document_id
            if chunk_id_val in ("", "unknown"):
                ev_dict["chunk_id"] = "chunk-aggregated"
            enriched_evidence.append(ev_dict)
        d["evidence"] = enriched_evidence
        enriched[cap] = d
    return enriched


def _demo_llm_extractor(prompt: str) -> str:
    """Legacy demo extractor kept for backwards compatibility."""
    return load_llm_extractor("demo")(prompt)


if __name__ == "__main__":
    # Demo 1: Raw text → IDP agent runs with demo LLM extractor.
    raw_doc = (
        "North Clinic is a regional hospital in Northern Ghana. "
        "We have oncology services, CT scanner, pathology lab, and ICU."
    )

    # Demo 2: Pre-extracted JSON with document_id and chunk_id in evidence.
    doc_pre_extracted = json.dumps({
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
            "confidence_scores": {k: 0.0 for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
            "extracted_evidence": {k: [] for k in ("oncology_services", "ct_scanner", "mri_scanner", "pathology_lab", "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator")},
            "suspicious_claims": ["world-class cancer center"],
        },
    })

    result = run_pipeline([raw_doc, doc_pre_extracted], llm_extractor=_demo_llm_extractor)
    print(json.dumps(result.model_dump(), indent=2))
