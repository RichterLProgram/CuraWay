"""Text-Utilities für NLP."""

import re
from typing import List


def split_sentences(text: str) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+", cleaned)
    sentences = [p.strip() for p in parts if p and p.strip()]
    return sentences if sentences else [cleaned]
