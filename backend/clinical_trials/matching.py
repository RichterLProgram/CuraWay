"""Regelbasiertes Matching von Patienten zu Clinical Trials."""

import math
import re
from typing import Dict, List, Optional, Tuple

from ai.med_bert import cosine_similarity, embed_texts
from ai.text_utils import split_sentences
from clinical_trials.models import EligibilitySignal, TrialMatch, TrialRecord
from patient.profile import PatientProfile


def match_trials(
    patient: PatientProfile, trials: List[TrialRecord]
) -> List[TrialMatch]:
    matches = []
    for trial in trials:
        score, signals = _score_trial(patient, trial)
        distance = _distance_to_closest_site(patient, trial)
        explanation = _build_explanation(trial)
        matches.append(
            TrialMatch(
                trial=trial,
                match_score=score,
                eligibility_signals=signals,
                distance_km=distance,
                explanation=explanation,
            )
        )
    return _rank_matches(matches)


def _score_trial(
    patient: PatientProfile, trial: TrialRecord
) -> Tuple[float, List[EligibilitySignal]]:
    criteria_raw = trial.eligibility_criteria or ""
    criteria = criteria_raw.lower()
    signals: List[EligibilitySignal] = []
    score = 1.0

    ai_constraints = _extract_constraints_ai(criteria_raw)
    biomarker_hits = ai_constraints.get("biomarkers") or _find_biomarker_requirements(criteria)
    for biomarker in biomarker_hits:
        evidence = ai_constraints.get("biomarker_evidence", {}).get(biomarker)
        evidence_conf = ai_constraints.get("biomarker_confidence", {}).get(biomarker)
        evidence_chunk = ai_constraints.get("biomarker_chunk", {}).get(biomarker)
        has_marker = _patient_has_biomarker(patient, biomarker)
        if has_marker is False:
            signals.append(
                EligibilitySignal(
                    key="biomarker",
                    passed=False,
                    detail=_detail_with_evidence(f"Missing biomarker: {biomarker}", evidence),
                    evidence_snippet=evidence,
                    evidence_confidence=evidence_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=evidence_chunk,
                )
            )
            score -= 0.45
        elif has_marker is None:
            signals.append(
                EligibilitySignal(
                    key="biomarker",
                    passed=None,
                    detail=_detail_with_evidence(f"Biomarker unclear: {biomarker}", evidence),
                    evidence_snippet=evidence,
                    evidence_confidence=evidence_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=evidence_chunk,
                )
            )
            score -= 0.15
        else:
            signals.append(
                EligibilitySignal(
                    key="biomarker",
                    passed=True,
                    detail=_detail_with_evidence(f"Biomarker present: {biomarker}", evidence),
                    evidence_snippet=evidence,
                    evidence_confidence=evidence_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=evidence_chunk,
                )
            )

    max_prior = ai_constraints.get("max_prior_therapies")
    if max_prior is None:
        max_prior = _find_max_prior_therapies(criteria)
    prior_evidence = ai_constraints.get("prior_therapy_evidence")
    prior_conf = ai_constraints.get("prior_therapy_confidence")
    prior_chunk = ai_constraints.get("prior_therapy_chunk")
    if max_prior is not None:
        if patient.prior_therapy_lines is None:
            signals.append(
                EligibilitySignal(
                    key="prior_therapies",
                    passed=None,
                    detail=_detail_with_evidence(f"Max prior therapies: {max_prior}", prior_evidence),
                    evidence_snippet=prior_evidence,
                    evidence_confidence=prior_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=prior_chunk,
                )
            )
            score -= 0.1
        elif patient.prior_therapy_lines > max_prior:
            signals.append(
                EligibilitySignal(
                    key="prior_therapies",
                    passed=False,
                    detail=_detail_with_evidence(
                        f"Too many prior therapies ({patient.prior_therapy_lines} > {max_prior})",
                        prior_evidence,
                    ),
                    evidence_snippet=prior_evidence,
                    evidence_confidence=prior_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=prior_chunk,
                )
            )
            score -= 0.5
        else:
            signals.append(
                EligibilitySignal(
                    key="prior_therapies",
                    passed=True,
                    detail=_detail_with_evidence(f"Prior therapies ok (≤{max_prior})", prior_evidence),
                    evidence_snippet=prior_evidence,
                    evidence_confidence=prior_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=prior_chunk,
                )
            )

    max_ecog = ai_constraints.get("ecog_max")
    if max_ecog is None:
        max_ecog = _find_ecog_max(criteria)
    ecog_evidence = ai_constraints.get("ecog_evidence")
    ecog_conf = ai_constraints.get("ecog_confidence")
    ecog_chunk = ai_constraints.get("ecog_chunk")
    if max_ecog is not None:
        if patient.ecog_status is None:
            signals.append(
                EligibilitySignal(
                    key="ecog",
                    passed=None,
                    detail=_detail_with_evidence(f"ECOG max {max_ecog}", ecog_evidence),
                    evidence_snippet=ecog_evidence,
                    evidence_confidence=ecog_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=ecog_chunk,
                )
            )
            score -= 0.1
        elif patient.ecog_status > max_ecog:
            signals.append(
                EligibilitySignal(
                    key="ecog",
                    passed=False,
                    detail=_detail_with_evidence(
                        f"ECOG too high ({patient.ecog_status} > {max_ecog})",
                        ecog_evidence,
                    ),
                    evidence_snippet=ecog_evidence,
                    evidence_confidence=ecog_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=ecog_chunk,
                )
            )
            score -= 0.5
        else:
            signals.append(
                EligibilitySignal(
                    key="ecog",
                    passed=True,
                    detail=_detail_with_evidence(f"ECOG ok (≤{max_ecog})", ecog_evidence),
                    evidence_snippet=ecog_evidence,
                    evidence_confidence=ecog_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=ecog_chunk,
                )
            )

    brain_mets_excluded = ai_constraints.get("exclude_brain_mets")
    if brain_mets_excluded is None:
        brain_mets_excluded = _excludes_brain_mets(criteria)
    brain_evidence = ai_constraints.get("brain_mets_evidence")
    brain_conf = ai_constraints.get("brain_mets_confidence")
    brain_chunk = ai_constraints.get("brain_mets_chunk")
    if brain_mets_excluded:
        if patient.brain_metastases is True:
            signals.append(
                EligibilitySignal(
                    key="brain_metastases",
                    passed=False,
                    detail=_detail_with_evidence("Brain metastases excluded", brain_evidence),
                    evidence_snippet=brain_evidence,
                    evidence_confidence=brain_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=brain_chunk,
                )
            )
            score -= 0.6
        elif patient.brain_metastases is None:
            signals.append(
                EligibilitySignal(
                    key="brain_metastases",
                    passed=None,
                    detail=_detail_with_evidence("Brain metastases status unclear", brain_evidence),
                    evidence_snippet=brain_evidence,
                    evidence_confidence=brain_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=brain_chunk,
                )
            )
            score -= 0.15
        else:
            signals.append(
                EligibilitySignal(
                    key="brain_metastases",
                    passed=True,
                    detail=_detail_with_evidence("No brain metastases", brain_evidence),
                    evidence_snippet=brain_evidence,
                    evidence_confidence=brain_conf,
                    evidence_document_id=_trial_doc_id(trial),
                    evidence_chunk_id=brain_chunk,
                )
            )

    score = max(0.0, min(1.0, score))
    score = _apply_phase_boost(score, trial.phase)
    return score, signals


def _apply_phase_boost(score: float, phase: Optional[str]) -> float:
    if not phase:
        return score
    phase_upper = phase.upper()
    if "PHASE 3" in phase_upper or "PHASE III" in phase_upper:
        return min(1.0, score + 0.08)
    if "PHASE 2" in phase_upper or "PHASE II" in phase_upper:
        return min(1.0, score + 0.04)
    return score


def _find_biomarker_requirements(criteria: str) -> List[str]:
    markers = []
    biomarker_terms = [
        "egfr", "kras", "alk", "ros1", "braf", "pd-l1", "her2", "met",
        "ret", "ntrk", "brca1", "brca2",
    ]
    for term in biomarker_terms:
        if re.search(rf"\b{re.escape(term)}\b", criteria):
            markers.append(term.upper() if term != "pd-l1" else "PD-L1")
    return markers


def _patient_has_biomarker(patient: PatientProfile, biomarker: str) -> Optional[bool]:
    if not patient.biomarkers:
        return None
    normalized = [b.upper().replace(" ", "") for b in patient.biomarkers]
    target = biomarker.upper().replace(" ", "")
    return target in normalized


def _find_max_prior_therapies(criteria: str) -> Optional[int]:
    match = re.search(r"(?:≤|<=|no more than|max(?:imum)?|up to)\s*(\d+)\s*prior", criteria)
    if match:
        return int(match.group(1))
    return None


def _find_ecog_max(criteria: str) -> Optional[int]:
    match = re.search(r"ECOG\s*(?:performance\s*status)?\s*0\s*[-–]\s*(\d)", criteria, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"ECOG\s*(?:performance\s*status)?\s*([0-4])\b", criteria, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _excludes_brain_mets(criteria: str) -> bool:
    return bool(
        re.search(r"no\s+(active\s+)?(brain|cns)\s+metast", criteria)
    )


def _distance_to_closest_site(
    patient: PatientProfile, trial: TrialRecord
) -> Optional[float]:
    if not patient.location or patient.location.latitude is None or patient.location.longitude is None:
        return None
    distances = []
    for loc in trial.locations:
        if loc.latitude is None or loc.longitude is None:
            continue
        distances.append(_haversine_km(
            patient.location.latitude,
            patient.location.longitude,
            loc.latitude,
            loc.longitude,
        ))
    return min(distances) if distances else None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _rank_matches(matches: List[TrialMatch]) -> List[TrialMatch]:
    def sort_key(match: TrialMatch):
        distance = match.distance_km if match.distance_km is not None else 10_000.0
        return (-match.match_score, distance)

    return sorted(matches, key=sort_key)


def _build_explanation(trial: TrialRecord) -> Optional[str]:
    if not trial.interventions and not trial.conditions:
        return None
    therapy = trial.interventions[0] if trial.interventions else "eine Behandlung"
    condition = trial.conditions[0] if trial.conditions else "Krebs"
    phase = f"({trial.phase}) " if trial.phase else ""
    return f"{phase}Study of {therapy} for {condition}."


def _detail_with_evidence(detail: str, evidence: Optional[str]) -> str:
    if evidence:
        return f"{detail} (Quote: \"{evidence}\")"
    return detail


def _extract_constraints_ai(criteria: str) -> Dict[str, object]:
    sentences = split_sentences(criteria)
    if not sentences:
        return {}
    try:
        sentence_embeddings = embed_texts(sentences)
    except Exception:
        return {}

    prompt_texts = {
        "biomarker": "biomarker requirement like EGFR KRAS PD-L1 mutation",
        "prior_therapy": "maximum prior therapies or lines of therapy",
        "ecog": "ECOG performance status requirement",
        "brain_mets": "exclusion of brain or CNS metastases",
    }
    prompts = list(prompt_texts.values())
    prompt_embeddings = embed_texts(prompts)
    prompt_map = dict(zip(prompt_texts.keys(), prompt_embeddings))

    slot_sentences: Dict[str, List[tuple[int, str]]] = {k: [] for k in prompt_texts}
    slot_scores: Dict[str, float] = {k: 0.0 for k in prompt_texts}
    for idx, sent in enumerate(sentences):
        for slot, prompt_vec in prompt_map.items():
            score = cosine_similarity(sentence_embeddings[idx], prompt_vec)
            if score >= 0.35:
                slot_sentences[slot].append((idx, sent))
                slot_scores[slot] = max(slot_scores[slot], score)

    biomarker_hits = _find_biomarker_requirements(" ".join(s for _, s in slot_sentences["biomarker"]))
    biomarker_evidence = {b: _first_sentence(slot_sentences["biomarker"]) for b in biomarker_hits}
    biomarker_confidence = {b: round(slot_scores["biomarker"], 3) for b in biomarker_hits}
    biomarker_chunk = {b: _first_chunk_id(slot_sentences["biomarker"]) for b in biomarker_hits}

    prior_sentence = _first_sentence(slot_sentences["prior_therapy"])
    ecog_sentence = _first_sentence(slot_sentences["ecog"])
    brain_sentence = _first_sentence(slot_sentences["brain_mets"])

    return {
        "biomarkers": biomarker_hits,
        "biomarker_evidence": biomarker_evidence,
        "biomarker_confidence": biomarker_confidence,
        "max_prior_therapies": _find_max_prior_therapies(" ".join(s for _, s in slot_sentences["prior_therapy"])),
        "prior_therapy_evidence": prior_sentence,
        "prior_therapy_confidence": round(slot_scores["prior_therapy"], 3) if prior_sentence else None,
        "prior_therapy_chunk": _first_chunk_id(slot_sentences["prior_therapy"]),
        "ecog_max": _find_ecog_max(" ".join(s for _, s in slot_sentences["ecog"])),
        "ecog_evidence": ecog_sentence,
        "ecog_confidence": round(slot_scores["ecog"], 3) if ecog_sentence else None,
        "ecog_chunk": _first_chunk_id(slot_sentences["ecog"]),
        "exclude_brain_mets": _excludes_brain_mets(" ".join(s for _, s in slot_sentences["brain_mets"])),
        "brain_mets_evidence": brain_sentence,
        "brain_mets_confidence": round(slot_scores["brain_mets"], 3) if brain_sentence else None,
        "brain_mets_chunk": _first_chunk_id(slot_sentences["brain_mets"]),
        "biomarker_chunk": biomarker_chunk,
    }


def _first_sentence(sentences: List[tuple[int, str]]) -> Optional[str]:
    if not sentences:
        return None
    return sentences[0][1][:220]


def _first_chunk_id(sentences: List[tuple[int, str]]) -> Optional[str]:
    if not sentences:
        return None
    return f"eligibility-sent-{sentences[0][0]:03d}"


def _trial_doc_id(trial: TrialRecord) -> str:
    return f"trial:{trial.nct_id}"
