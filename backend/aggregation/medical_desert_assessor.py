"""Deterministic regional aggregation for medical desert risk."""

import json
from collections import defaultdict
from typing import Dict, List

from models.shared import (
    FacilityWithCapabilityDecisions,
    RegionalAssessment,
    RegionalRiskLevel,
)


def assess_medical_desert(
    facilities: List[FacilityWithCapabilityDecisions],
) -> List[RegionalAssessment]:
    """
    Assess medical desert risk by region using finalized capability decisions.

    The logic is conservative: missing or uncertain capabilities reduce
    coverage and increase risk. No LLM calls or side effects.
    """
    grouped: Dict[str, List[FacilityWithCapabilityDecisions]] = defaultdict(list)
    for facility in facilities:
        region = facility.region or "unknown"
        grouped[region].append(facility)

    assessments: List[RegionalAssessment] = []
    essential_capabilities = [
        "oncology_services",
        "ct_scanner",
        "mri_scanner",
        "pathology_lab",
        "chemotherapy_delivery",
        "icu",
    ]

    for region, region_facilities in grouped.items():
        facility_ids = [f.facility_id for f in region_facilities]
        coverage_flags: Dict[str, bool] = {cap: False for cap in essential_capabilities}

        for facility in region_facilities:
            for capability in essential_capabilities:
                decision = facility.capability_decisions.get(capability, {})
                # Conservative interpretation: only count True when a decision
                # explicitly marks the capability as True with direct evidence.
                if decision.get("value") is True and decision.get(
                    "decision_reason"
                ) == "direct_evidence":
                    coverage_flags[capability] = True

        covered = sum(1 for cap in essential_capabilities if coverage_flags[cap])
        total = len(essential_capabilities)
        coverage_score = round(covered / total, 3)

        # Thresholds are conservative to avoid underestimating risk:
        # - high risk if fewer than 2 essential capabilities are present.
        # - medium risk if fewer than 4 are present.
        if covered < 2:
            risk_level = RegionalRiskLevel(level="high")
        elif covered < 4:
            risk_level = RegionalRiskLevel(level="medium")
        else:
            risk_level = RegionalRiskLevel(level="low")

        missing = [cap for cap in essential_capabilities if not coverage_flags[cap]]
        explanation = (
            f"Region '{region}' has {covered}/{total} essential capabilities "
            f"confirmed across facilities {facility_ids}. Missing: {missing}."
        )

        assessments.append(
            RegionalAssessment(
                region=region,
                coverage_score=coverage_score,
                risk_level=risk_level,
                explanation=explanation,
                facility_ids=facility_ids,
            )
        )

    return assessments


if __name__ == "__main__":
    sample_facilities = [
        FacilityWithCapabilityDecisions(
            facility_id="FAC-001",
            region="North",
            capability_decisions={
                "ct_scanner": {
                    "value": True,
                    "confidence": 0.8,
                    "decision_reason": "direct_evidence",
                    "evidence": [
                        {"text": "16-slice CT scanner", "document_id": "doc1", "chunk_id": "c1"}
                    ],
                },
                "icu": {
                    "value": True,
                    "confidence": 0.7,
                    "decision_reason": "direct_evidence",
                    "evidence": [
                        {"text": "ICU with 8 beds", "document_id": "doc1", "chunk_id": "c2"}
                    ],
                },
            },
        ),
        FacilityWithCapabilityDecisions(
            facility_id="FAC-002",
            region="North",
            capability_decisions={
                "pathology_lab": {
                    "value": True,
                    "confidence": 0.65,
                    "decision_reason": "direct_evidence",
                    "evidence": [
                        {"text": "Pathology lab onsite", "document_id": "doc2", "chunk_id": "c3"}
                    ],
                },
                "oncology_services": {
                    "value": False,
                    "confidence": 0.3,
                    "decision_reason": "insufficient_evidence",
                    "evidence": [],
                },
            },
        ),
        FacilityWithCapabilityDecisions(
            facility_id="FAC-003",
            region="South",
            capability_decisions={
                "chemotherapy_delivery": {
                    "value": False,
                    "confidence": 0.4,
                    "decision_reason": "suspicious_claim",
                    "evidence": [],
                },
            },
        ),
    ]

    result = assess_medical_desert(sample_facilities)
    # Example JSON output for NGO-facing audit trails:
    # - North is medium risk: 3/6 essentials confirmed (CT, ICU, pathology).
    # - South is high risk: 0/6 essentials confirmed.
    print(json.dumps([r.dict() for r in result], indent=2))
