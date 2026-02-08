from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import yaml

from src.ontology.negation import detect_negated_mentions
from src.shared.models import SupplyEntry


_ONTOLOGY_CACHE: Optional[Dict[str, Any]] = None


def load_ontology() -> Dict[str, Any]:
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is not None:
        return _ONTOLOGY_CACHE

    path = os.path.join(os.path.dirname(__file__), "capability_ontology.yaml")
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    _ONTOLOGY_CACHE = data
    return data


def normalize_capability_name(name: str) -> Dict[str, Any]:
    ontology = load_ontology()
    capabilities = ontology.get("capabilities", {})
    name_norm = _normalize_text(name)

    code_match = name if name in capabilities else name.strip().upper()
    if code_match in capabilities:
        info = capabilities.get(code_match, {})
        display_name = str(info.get("display_name", name))
        return {
            "code": code_match,
            "display_name": display_name,
            "match_type": "code",
            "confidence": 1.0,
        }

    best = {"code": None, "display_name": name, "match_type": "none", "confidence": 0.0}

    for code, info in capabilities.items():
        display_name = str(info.get("display_name", code))
        synonyms = [display_name] + list(info.get("synonyms", []))

        for synonym in synonyms:
            synonym_norm = _normalize_text(str(synonym))
            if not synonym_norm:
                continue
            if synonym_norm == name_norm:
                return {
                    "code": code,
                    "display_name": display_name,
                    "match_type": "synonym",
                    "confidence": 0.95,
                }

        if _token_subset_match(name_norm, synonyms):
            best = {
                "code": code,
                "display_name": display_name,
                "match_type": "token",
                "confidence": 0.6,
            }

    return best


def normalize_supply(supply_json: Any, source_text: Optional[str] = None) -> Any:
    capabilities = _normalize_entries(
        getattr(supply_json, "capabilities", []), source_text=source_text
    )
    equipment = _normalize_entries(
        getattr(supply_json, "equipment", []), source_text=source_text
    )
    specialists = _normalize_entries(
        getattr(supply_json, "specialists", []), source_text=source_text
    )

    supply_json.capabilities = capabilities
    supply_json.equipment = equipment
    supply_json.specialists = specialists
    supply_json.canonical_capabilities = _dedupe_codes(
        capabilities + equipment + specialists
    )
    supply_json.capabilities_legacy = [entry.name for entry in capabilities]
    supply_json.equipment_legacy = [entry.name for entry in equipment]
    supply_json.specialists_legacy = [entry.name for entry in specialists]
    return supply_json


def _normalize_entries(entries: Any, source_text: Optional[str] = None) -> List[SupplyEntry]:
    results: List[SupplyEntry] = []
    for entry in entries or []:
        if isinstance(entry, SupplyEntry):
            name = entry.name
            citation_ids = list(entry.citation_ids)
            capability_code = entry.capability_code
            confidence = entry.confidence
            evidence = entry.evidence
        elif isinstance(entry, dict):
            name = str(entry.get("name") or "")
            citation_ids = list(entry.get("citation_ids") or [])
            capability_code = entry.get("capability_code")
            confidence = entry.get("confidence")
            evidence = entry.get("evidence")
        else:
            name = str(entry)
            citation_ids = []
            capability_code = None
            confidence = None
            evidence = None

        if not capability_code and name:
            normalized = normalize_capability_name(name)
            capability_code = normalized.get("code")
            confidence = normalized.get("confidence")

        negated = None
        if source_text and capability_code:
            synonyms = _synonyms_for_code(capability_code)
            if synonyms:
                negated = detect_negated_mentions(source_text, synonyms)

        results.append(
            SupplyEntry(
                name=name,
                citation_ids=citation_ids,
                capability_code=capability_code,
                confidence=confidence,
                negated=negated,
                evidence=evidence,
            )
        )
    return results


def _dedupe_codes(entries: List[SupplyEntry]) -> List[str]:
    codes = []
    for entry in entries:
        if entry.capability_code and entry.capability_code not in codes:
            codes.append(entry.capability_code)
    return codes


def _normalize_text(text: str) -> str:
    return re.sub(r"[\s\-_]+", " ", text.strip().lower())


def _token_subset_match(name_norm: str, synonyms: List[str]) -> bool:
    name_tokens = set(name_norm.split())
    if not name_tokens:
        return False
    for synonym in synonyms:
        synonym_norm = _normalize_text(str(synonym))
        synonym_tokens = set(synonym_norm.split())
        if synonym_tokens and synonym_tokens.issubset(name_tokens):
            return True
    return False


def _synonyms_for_code(code: str) -> List[str]:
    ontology = load_ontology()
    info = (ontology.get("capabilities") or {}).get(code, {})
    display_name = str(info.get("display_name", code))
    synonyms = [display_name] + list(info.get("synonyms", []))
    return [syn for syn in synonyms if syn]
