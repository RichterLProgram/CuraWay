"""Pluggable extractors for IDP prompts."""

import json
import os
import re
from typing import Callable, Dict, List, Tuple
from urllib import request

from features.validation.anomaly_validator import detect_suspicious_claims


def load_llm_extractor(mode: str | None = None) -> Callable[[str], str]:
    selected = (mode or os.getenv("LLM_EXTRACTOR_MODE") or "demo").lower().strip()
    if selected == "rules":
        return rules_extractor
    if selected in {"http", "databricks", "openai"}:
        return http_extractor
    return demo_extractor


def demo_extractor(prompt: str) -> str:
    """Demo extractor for raw text. Mimics an LLM response."""
    text = _prompt_text(prompt)
    has_cap = "North" in text
    payload = {
        "facility_name": "North Clinic" if "North" in text else "South Clinic",
        "country": "GH",
        "region": "North" if "North" in text else "South",
        "capabilities": {
            "oncology_services": {"value": has_cap and "oncology" in text.lower(), "confidence": 0.7 if has_cap else 0.0, "evidence": ["oncology services onsite"] if has_cap else []},
            "ct_scanner": {"value": has_cap and "ct" in text.lower(), "confidence": 0.8 if has_cap else 0.0, "evidence": ["CT scanner available"] if has_cap else []},
            "mri_scanner": {"value": False, "confidence": 0.0, "evidence": []},
            "pathology_lab": {"value": has_cap and "pathology" in text.lower(), "confidence": 0.75 if has_cap else 0.0, "evidence": ["pathology lab available"] if has_cap else []},
            "genomic_testing": {"value": False, "confidence": 0.0, "evidence": []},
            "chemotherapy_delivery": {"value": False, "confidence": 0.0, "evidence": []},
            "radiotherapy": {"value": False, "confidence": 0.0, "evidence": []},
            "icu": {"value": has_cap and "icu" in text.lower(), "confidence": 0.8 if has_cap else 0.0, "evidence": ["ICU with 6 beds"] if has_cap else []},
            "trial_coordinator": {"value": False, "confidence": 0.0, "evidence": []},
        },
        "suspicious_claims": [],
    }
    return json.dumps(payload)


def rules_extractor(prompt: str) -> str:
    """Deterministic keyword extractor with line-level citations."""
    text = _prompt_text(prompt)
    document_id = _extract_document_id(text)
    lines = [line for line in text.splitlines() if line.strip()]

    capability_keywords: Dict[str, List[str]] = {
        "oncology_services": ["oncology", "cancer", "oncology clinic"],
        "ct_scanner": ["ct", "computed tomography"],
        "mri_scanner": ["mri", "magnetic resonance"],
        "pathology_lab": ["pathology", "lab"],
        "genomic_testing": ["genomic", "genetics", "sequencing"],
        "chemotherapy_delivery": ["chemotherapy", "chemo"],
        "radiotherapy": ["radiotherapy", "radiation therapy"],
        "icu": ["icu", "intensive care"],
        "trial_coordinator": ["trial", "research coordinator"],
    }

    capabilities: Dict[str, Dict[str, object]] = {}
    for cap, keywords in capability_keywords.items():
        matches = _find_keyword_lines(lines, keywords)
        evidence = [
            {
                "text": match,
                "document_id": document_id,
                "chunk_id": _line_chunk_id(match),
            }
            for match in matches
        ]
        capabilities[cap] = {
            "value": bool(evidence),
            "confidence": 0.72 if evidence else 0.05,
            "evidence": evidence,
        }

    payload = {
        "facility_name": _guess_facility_name(lines),
        "country": _guess_country(lines),
        "region": _guess_region(lines),
        "capabilities": capabilities,
        "suspicious_claims": detect_suspicious_claims(text),
    }
    return json.dumps(payload)


def http_extractor(prompt: str) -> str:
    """
    Generic HTTP extractor for external LLMs or Databricks serving.
    Expected env:
      - LLM_HTTP_URL (required)
      - LLM_HTTP_TOKEN (optional)
    Response may contain: output, text, or choices[0].text/message.content.
    """
    url = os.getenv("LLM_HTTP_URL")
    if not url:
        return demo_extractor(prompt)
    token = os.getenv("LLM_HTTP_TOKEN", "")
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8")
            return _extract_text_from_response(body) or demo_extractor(prompt)
    except Exception:
        return demo_extractor(prompt)


def _prompt_text(prompt: str) -> str:
    return prompt.split("TEXT:\n", 1)[-1] if "TEXT:\n" in prompt else prompt


def _extract_text_from_response(body: str) -> str | None:
    try:
        data = json.loads(body)
    except Exception:
        return None
    if isinstance(data, dict):
        if isinstance(data.get("output"), str):
            return data["output"]
        if isinstance(data.get("text"), str):
            return data["text"]
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                if isinstance(first.get("text"), str):
                    return first["text"]
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
    return None


def _extract_document_id(text: str) -> str:
    for line in text.splitlines()[:3]:
        if line.startswith("DOCUMENT_ID:"):
            return line.split("DOCUMENT_ID:", 1)[-1].strip() or "unknown"
    return "unknown"


def _line_chunk_id(line: str) -> str:
    match = re.match(r"^L(\d+)\|", line)
    if match:
        return f"line-{match.group(1)}"
    return "unknown"


def _find_keyword_lines(lines: List[str], keywords: List[str]) -> List[str]:
    hits = []
    for line in lines:
        lower = line.lower()
        if any(keyword in lower for keyword in keywords):
            hits.append(line.strip())
    return hits


def _guess_facility_name(lines: List[str]) -> str:
    for line in lines[:5]:
        if "clinic" in line.lower() or "hospital" in line.lower():
            return _strip_line_prefix(line)
    return "Unknown Facility"


def _guess_country(lines: List[str]) -> str | None:
    for line in lines[:8]:
        if "ghana" in line.lower() or "gh" in line.lower():
            return "GH"
    return None


def _guess_region(lines: List[str]) -> str | None:
    for line in lines[:12]:
        if "north" in line.lower():
            return "North"
        if "south" in line.lower():
            return "South"
    return None


def _strip_line_prefix(line: str) -> str:
    return re.sub(r"^L\d+\|", "", line).strip()
