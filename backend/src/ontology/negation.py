from __future__ import annotations

import re
from typing import Iterable


NEGATION_PATTERNS = [
    r"\bno\b",
    r"\bwithout\b",
    r"\bnot available\b",
    r"\bdoesn'?t have\b",
    r"\blacks?\b",
    r"\bunavailable\b",
]


def detect_negated_mentions(text: str, terms: Iterable[str], window: int = 4) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for term in terms:
        term_norm = str(term).strip().lower()
        if not term_norm:
            continue
        if term_norm not in text_lower:
            continue
        if _has_negation_near(text_lower, term_norm, window):
            return True
    return False


def _has_negation_near(text_lower: str, term: str, window: int) -> bool:
    tokens = re.findall(r"\w+|\S", text_lower)
    term_tokens = term.split()
    if not term_tokens:
        return False
    for idx in range(len(tokens)):
        if tokens[idx : idx + len(term_tokens)] == term_tokens:
            start = max(0, idx - window)
            end = min(len(tokens), idx + len(term_tokens) + window)
            window_tokens = " ".join(tokens[start:end])
            if any(re.search(pattern, window_tokens) for pattern in NEGATION_PATTERNS):
                return True
    return False
