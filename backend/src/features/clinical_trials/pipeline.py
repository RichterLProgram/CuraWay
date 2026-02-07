"""Orchestrierung für Clinical-Trial-Matching."""

from typing import List

from features.clinical_trials.api_client import fetch_trials
from features.clinical_trials.geocoding import geocode_location
from features.clinical_trials.matching import match_trials
from features.clinical_trials.models import TrialMatchingResult, TrialSummary
from features.clinical_trials.reference_data import load_reference_data
from features.patient.profile_extractor import extract_patient_profile_with_evidence


def run_trial_matching(documents: List[str]) -> List[TrialMatchingResult]:
    results: List[TrialMatchingResult] = []
    reference_data = load_reference_data()
    for idx, doc in enumerate(documents, start=1):
        doc_id = f"patient-report-{idx:03d}"
        extraction = extract_patient_profile_with_evidence(doc, document_id=doc_id)
        patient = extraction.profile
        if patient.location and (patient.location.latitude is None or patient.location.longitude is None):
            geo = geocode_location(patient.location.label or "")
            if geo:
                patient.location.latitude = geo.latitude
                patient.location.longitude = geo.longitude
        query = _build_query(patient)
        trials = fetch_trials(query=query, page_size=60)
        matches = match_trials(patient, trials)
        top_matches = _build_top_summaries(matches, limit=3)
        results.append(
            TrialMatchingResult(
                patient_profile=patient,
                patient_evidence=[e.model_dump() for e in extraction.evidence],
                extraction_method=extraction.method,
                query=query,
                matches=matches,
                top_matches=top_matches,
                reference_data=reference_data,
                agent_trace=_build_agent_trace(extraction, matches),
            )
        )
    return results


def _build_query(patient) -> str:
    parts = []
    if patient.cancer_type:
        parts.append(patient.cancer_type)
    if patient.biomarkers:
        parts.append(patient.biomarkers[0])
    if not parts:
        return "cancer"
    return " ".join(parts)


def _build_top_summaries(matches, limit: int) -> List[TrialSummary]:
    summaries: List[TrialSummary] = []
    for match in matches[:limit]:
        summaries.append(
            TrialSummary(
                nct_id=match.trial.nct_id,
                title=match.trial.title,
                match_score=match.match_score,
                phase=match.trial.phase,
                status=match.trial.status,
                distance_km=match.distance_km,
                travel_time_minutes=match.travel_time_minutes,
                explanation=match.explanation,
            )
        )
    return summaries


def _build_agent_trace(extraction, matches) -> dict:
    eligibility_count = sum(len(m.eligibility_signals) for m in matches)
    return {
        "patient_extraction_agent": {
            "agent_id": "agent.patient_extractor.v1",
            "method": extraction.method,
            "evidence_items": len(extraction.evidence),
            "provenance": [e.model_dump() for e in extraction.evidence],
        },
        "matching_agent": {
            "agent_id": "agent.trial_matcher.v1",
            "matches": len(matches),
            "eligibility_signals": eligibility_count,
            "provenance": [
                {
                    "trial_id": m.trial.nct_id,
                    "signals": [
                        {
                            "key": s.key,
                            "passed": s.passed,
                            "evidence_snippet": s.evidence_snippet,
                            "evidence_confidence": s.evidence_confidence,
                            "document_id": s.evidence_document_id,
                            "chunk_id": s.evidence_chunk_id,
                        }
                        for s in m.eligibility_signals
                        if s.evidence_snippet
                    ],
                }
                for m in matches
            ],
        },
    }
