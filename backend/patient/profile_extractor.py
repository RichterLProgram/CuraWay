"""Heuristic patient profile extraction from report text."""

import re
from typing import List, Optional

from ai.med_bert import cosine_similarity, embed_texts
from ai.text_utils import split_sentences
from patient.profile import PatientEvidenceItem, PatientExtractionResult, PatientLocation, PatientProfile

_CANCER_PATTERNS = [
    (r"\bnsclc\b", "Non-Small Cell Lung Cancer"),
    (r"non[-\s]?small cell lung cancer", "Non-Small Cell Lung Cancer"),
    (r"lung adenocarcinoma", "Lung Adenocarcinoma"),
    (r"lung cancer", "Lung Cancer"),
    (r"breast cancer|mammakarzinom", "Breast Cancer"),
    (r"colorectal cancer|kolorektal", "Colorectal Cancer"),
    (r"ovarian cancer|ovar", "Ovarian Cancer"),
    (r"pancreatic cancer|pankreas", "Pancreatic Cancer"),
    (r"prostate cancer|prostatakarzinom", "Prostate Cancer"),
    (r"melanoma|melanom", "Melanoma"),
    (r"glioblastoma", "Glioblastoma"),
]

_BIOMARKERS = [
    "EGFR", "KRAS", "ALK", "ROS1", "BRAF", "PD-L1", "HER2", "MET",
    "RET", "NTRK", "BRCA1", "BRCA2", "PIK3CA", "TP53",
]

_BIOMARKER_ALIASES = {
    "PDL1": "PD-L1",
    "HER-2": "HER2",
    "ERBB2": "HER2",
    "BRCA-1": "BRCA1",
    "BRCA-2": "BRCA2",
}


def extract_patient_profile(text: str) -> PatientProfile:
    return extract_patient_profile_with_evidence(text).profile


def extract_patient_profile_with_evidence(text: str, document_id: str = "patient-report") -> PatientExtractionResult:
    ai_result = _extract_with_ai(text, document_id)
    if ai_result is not None:
        return ai_result
    return _extract_with_rules(text, document_id)


def _extract_with_ai(text: str, document_id: str) -> Optional[PatientExtractionResult]:
    sentences = split_sentences(text)
    if not sentences:
        return None
    try:
        sentence_embeddings = embed_texts(sentences)
    except Exception:
        return None

    slot_prompts = {
        "cancer_type": "cancer diagnosis or tumor type",
        "stage": "cancer stage or stadium",
        "biomarkers": "biomarkers or genetic mutation like EGFR KRAS PD-L1",
        "prior_therapy": "prior therapy lines or previous systemic therapy",
        "ecog": "ECOG performance status",
        "brain_mets": "brain metastases or CNS metastases status",
        "location": "patient location city address",
    }
    prompt_texts = list(slot_prompts.values())
    prompt_embeddings = embed_texts(prompt_texts)
    prompt_map = dict(zip(slot_prompts.keys(), prompt_embeddings))

    slot_sentences: dict[str, List[tuple[int, str]]] = {k: [] for k in slot_prompts}
    slot_scores: dict[str, float] = {k: 0.0 for k in slot_prompts}
    for idx, sent in enumerate(sentences):
        for slot, prompt_vec in prompt_map.items():
            score = cosine_similarity(sentence_embeddings[idx], prompt_vec)
            if score >= 0.35:
                slot_sentences[slot].append((idx, sent))
                slot_scores[slot] = max(slot_scores[slot], score)

    text_focus = {
        "cancer_type": " ".join(s for _, s in slot_sentences["cancer_type"]) or text,
        "stage": " ".join(s for _, s in slot_sentences["stage"]) or text,
        "biomarkers": " ".join(s for _, s in slot_sentences["biomarkers"]) or text,
        "prior_therapy": " ".join(s for _, s in slot_sentences["prior_therapy"]) or text,
        "ecog": " ".join(s for _, s in slot_sentences["ecog"]) or text,
        "brain_mets": " ".join(s for _, s in slot_sentences["brain_mets"]) or text,
        "location": " ".join(s for _, s in slot_sentences["location"]) or text,
    }

    evidence_items = []
    for field, sentences_for_field in slot_sentences.items():
        if not sentences_for_field:
            continue
        idx, sentence = sentences_for_field[0]
        evidence_items.append(
            PatientEvidenceItem(
                field=field,
                snippet=sentence[:240],
                confidence=round(slot_scores[field], 3),
                document_id=document_id,
                chunk_id=f"sent-{idx:03d}",
            )
        )

    return PatientExtractionResult(
        profile=PatientProfile(
            cancer_type=_extract_cancer_type(text_focus["cancer_type"]),
            stage=_extract_stage(text_focus["stage"]),
            biomarkers=_extract_biomarkers(text_focus["biomarkers"]),
            prior_therapy_lines=_extract_prior_therapy_lines(text_focus["prior_therapy"]),
            ecog_status=_extract_ecog(text_focus["ecog"]),
            brain_metastases=_extract_brain_metastases(text_focus["brain_mets"]),
            location=_extract_location(text_focus["location"]),
        ),
        evidence=evidence_items,
        method="med-bert",
    )


def _extract_with_rules(text: str, document_id: str) -> PatientExtractionResult:
    cleaned = " ".join(text.split())
    cancer_type = _extract_cancer_type(cleaned)
    stage = _extract_stage(cleaned)
    biomarkers = _extract_biomarkers(cleaned)
    prior_lines = _extract_prior_therapy_lines(cleaned)
    ecog = _extract_ecog(cleaned)
    brain_mets = _extract_brain_metastases(cleaned)
    location = _extract_location(cleaned)

    return PatientExtractionResult(
        profile=PatientProfile(
            cancer_type=cancer_type,
            stage=stage,
            biomarkers=biomarkers,
            prior_therapy_lines=prior_lines,
            ecog_status=ecog,
            brain_metastases=brain_mets,
            location=location,
        ),
        evidence=[],
        method="rules",
    )


def _extract_cancer_type(text: str) -> Optional[str]:
    for pattern, name in _CANCER_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return name
    return None


def _extract_stage(text: str) -> Optional[str]:
    match = re.search(r"\b(stadium|stage)\s*([IVX]+[A-C]?)\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(2).upper()
    match = re.search(r"\b([IVX]+[A-C]?)\s*(stadium|stage)\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"\b(stage)\s*(\d)\b", text, flags=re.IGNORECASE)
    if match:
        return match.group(2)
    return None


def _extract_biomarkers(text: str) -> List[str]:
    markers = set()
    for marker in _BIOMARKERS:
        if re.search(rf"\b{re.escape(marker)}\b", text, flags=re.IGNORECASE):
            markers.add(marker)
    for alias, canonical in _BIOMARKER_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", text, flags=re.IGNORECASE):
            markers.add(canonical)

    if re.search(r"exon\s*19\s*del", text, flags=re.IGNORECASE):
        markers.add("EGFR exon 19 deletion")
    if re.search(r"\bL858R\b", text, flags=re.IGNORECASE):
        markers.add("EGFR L858R")
    if re.search(r"\bEGFR\b.*\bmutation\b", text, flags=re.IGNORECASE):
        markers.add("EGFR mutation")

    return sorted(markers)


def _extract_prior_therapy_lines(text: str) -> Optional[int]:
    match = re.search(
        r"\b(\d+)\s*(prior|previous|vor)\s*(systemic\s*)?therap",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return int(match.group(1))

    match = re.search(r"\b(1st|2nd|3rd|4th)\s*line\b", text, flags=re.IGNORECASE)
    if match:
        order = {"1st": 0, "2nd": 1, "3rd": 2, "4th": 3}
        return order.get(match.group(1).lower())

    match = re.search(r"\b(\d+)\s*(vorbehandlung|vortherap|therapielinien)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _extract_ecog(text: str) -> Optional[int]:
    match = re.search(r"\bECOG(?:\s*Performance\s*Status)?\s*([0-4])\b", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"\bECOG\s*([0-4])\s*[-–]\s*([0-4])\b", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(2))
    return None


def _extract_brain_metastases(text: str) -> Optional[bool]:
    if re.search(
        r"(no|keine)\s+(active\s+)?(brain|cns|hirn|zns)\s+metast",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    if re.search(r"(brain|cns|hirn|zns)\s+metast", text, flags=re.IGNORECASE):
        return True
    return None


def _extract_location(text: str) -> Optional[PatientLocation]:
    match = re.search(
        r"\b(lat(?:itude)?|breitengrad)\s*[:=]\s*([-+]?\d+\.\d+)\b.*?\b(lon(?:gitude)?|laengengrad)\s*[:=]\s*([-+]?\d+\.\d+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        return PatientLocation(
            latitude=float(match.group(2)),
            longitude=float(match.group(4)),
        )
    match = re.search(
        r"(location|wohnort|city)\s*[:\-]\s*([A-Za-zÄÖÜäöüß\s]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    label = match.group(2).strip()
    return PatientLocation(label=label)
