"""Suspicious / conflict detection."""

import re
from typing import List


def detect_suspicious_claims(text: str) -> List[str]:
    """Detect marketing-style suspicious claims in text."""
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


def is_negated(text: str) -> bool:
    """Check if evidence snippet contains negation."""
    lowered = text.lower()
    negations = ["no ", "not ", "without ", "none ", "lack ", "lacks ", "absent "]
    return any(token in lowered for token in negations)


def suspicious_for_capability(capability: str, claims: List[str]) -> bool:
    """Check if any suspicious claim appears to mention this capability."""
    keywords = {
        "oncology_services": ["oncology", "cancer"],
        "ct_scanner": ["ct", "computed tomography"],
        "mri_scanner": ["mri", "magnetic resonance"],
        "pathology_lab": ["pathology", "lab"],
        "genomic_testing": ["genomic", "genetics", "sequencing"],
        "chemotherapy_delivery": ["chemotherapy"],
        "radiotherapy": ["radiotherapy", "radiation"],
        "icu": ["icu", "intensive care"],
        "trial_coordinator": ["trial", "research"],
    }
    tokens = keywords.get(capability, [])
    for claim in claims:
        lowered = claim.lower()
        if any(token in lowered for token in tokens):
            return True
    return False
