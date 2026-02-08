from __future__ import annotations

import re
from typing import Dict, List

from langchain_core.tools import tool


@tool
def validate_medical_response(answer: str, sources: List) -> Dict:
    """
    Validate medical response for safety concerns.
    Heuristic checks:
    - Dosage without sources -> warning
    - Directive advice without sources -> warning
    """
    warnings: List[str] = []

    dosage_patterns = [r"\d+\s*mg\b", r"\d+\s*mcg\b", r"\bdose\b", r"\bDosis\b"]
    has_dosage = any(
        re.search(pattern, answer, re.IGNORECASE) for pattern in dosage_patterns
    )

    directive_patterns = [r"\byou should\b", r"\bSie sollten\b", r"\bmust take\b", r"\bmüssen\b"]
    has_directive = any(
        re.search(pattern, answer, re.IGNORECASE) for pattern in directive_patterns
    )

    if has_dosage and not sources:
        warnings.append("Answer contains dosage information without cited sources")

    if has_directive and not sources:
        warnings.append("Answer provides directive medical advice without cited sources")

    status = "warning" if warnings else "ok"

    return {
        "status": status,
        "notes": warnings if warnings else ["No safety concerns detected"],
    }
