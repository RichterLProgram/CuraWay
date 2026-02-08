from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from src.ontology.normalize import normalize_capability_name
from src.supply.evidence_index import find_evidence_for_code

class Issue(BaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    path: str
    evidence: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    verdict: Literal["plausible", "suspicious", "impossible"]
    score: float = Field(ge=0, le=1)
    issues: List[Issue] = Field(default_factory=list)
    issue_count_by_severity: Dict[str, int] = Field(default_factory=dict)
    normalized_supply: Optional[Dict[str, Any]] = None
    trace_id: str
    explanation: str = ""
    llm_verdict: Optional[Literal["plausible", "suspicious", "impossible"]] = None
    llm_rationale: Optional[str] = None
    llm_evidence_refs: List[str] = Field(default_factory=list)


DEFAULT_SCHEMA = {
    "required_fields": [
        "facility_id",
        "name",
        "location",
        "capabilities",
        "equipment",
        "specialists",
    ],
    "required_severity": {
        "facility_id": "error",
        "name": "error",
        "location": "error",
    },
    "type_expectations": {
        "facility_id": "string",
        "name": "string",
        "location": "object",
        "capabilities": "list",
        "equipment": "list",
        "specialists": "list",
        "coverage_score": "number",
    },
}

DEFAULT_CONSTRAINTS = {
    "confidence_threshold": 0.4,
    "rules": [
        {
            "code": "CT_MRI_REQUIRES_RADIOLOGY",
            "when_any": ["IMAGING_CT", "IMAGING_MRI"],
            "requires_any": ["SPECIALIST_RADIOLOGY", "radiologist_count"],
            "severity": "warning",
            "verdict": "suspicious",
            "message": "CT/MRI capability requires radiology staff or radiologist count > 0.",
            "path": "canonical_capabilities",
        },
        {
            "code": "SURGERY_REQUIRES_OT_ANESTHESIA",
            "when_any": ["SURGERY_GENERAL", "SURGERY_OT"],
            "requires_all": ["SURGERY_OT"],
            "requires_any": ["ANESTHESIA", "SPECIALIST_ANESTHESIA", "anesthesia_staff"],
            "severity": "warning",
            "verdict": "suspicious",
            "message": "Surgery capability requires an operating theatre and anesthesia.",
            "path": "canonical_capabilities",
        },
        {
            "code": "ICU_REQUIRES_VENTILATORS_STAFF",
            "when_any": ["ICU"],
            "requires_any": ["EQUIP_VENTILATOR", "SPECIALIST_CRITICAL_CARE", "critical_care_staff"],
            "severity": "warning",
            "verdict": "suspicious",
            "message": "ICU capability requires ventilators or critical care staff > 0.",
            "path": "canonical_capabilities",
        },
        {
            "code": "BLOOD_TRANSFUSION_REQUIRES_BANK_OR_LAB",
            "when_any": ["LAB_BLOODBANK"],
            "requires_any": ["LAB_BLOODBANK", "LAB_GENERAL"],
            "severity": "warning",
            "verdict": "suspicious",
            "message": "Blood transfusion requires blood bank or lab capability.",
            "path": "canonical_capabilities",
        },
        {
            "code": "NO_IMAGING_CONTRADICTION",
            "when_any": ["IMAGING_NONE"],
            "forbid_any": ["IMAGING_CT", "IMAGING_MRI", "IMAGING_XRAY", "IMAGING_ULTRASOUND"],
            "severity": "error",
            "verdict": "impossible",
            "message": "Imaging listed but facility marked as no imaging.",
            "path": "canonical_capabilities",
        },
    ],
}


def validate_supply(
    supply_json: Dict[str, Any],
    facility_schema: Optional[Dict[str, Any]] = None,
    constraints_config: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> ValidationResult:
    trace_id = trace_id or str(uuid.uuid4())
    issues: List[Issue] = []
    verdict: Literal["plausible", "suspicious", "impossible"] = "plausible"

    schema_config = _extract_schema_config(facility_schema)
    constraints = _load_constraints_config(constraints_config)

    normalized = _normalize_supply(supply_json)

    verdict = _run_schema_checks(
        supply_json, schema_config, issues, verdict
    )
    verdict = _run_range_checks(supply_json, issues, verdict)
    verdict = _run_constraint_checks(normalized, constraints, issues, verdict)
    verdict = _run_confidence_checks(supply_json, constraints, issues, verdict)

    issue_count_by_severity = _count_by_severity(issues)
    score = _score_from_issues(issues)
    explanation = _build_explanation(verdict, issues)

    return ValidationResult(
        verdict=verdict,
        score=score,
        issues=issues,
        issue_count_by_severity=issue_count_by_severity,
        normalized_supply=normalized,
        trace_id=trace_id,
        explanation=explanation,
    )


def _extract_schema_config(facility_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not facility_schema:
        return DEFAULT_SCHEMA

    if "required" in facility_schema and "properties" in facility_schema:
        required_fields = facility_schema.get("required", [])
        properties = facility_schema.get("properties", {})
        type_expectations = {}
        for field, schema in properties.items():
            schema_type = schema.get("type")
            if schema_type:
                type_expectations[field] = _normalize_schema_type(schema_type)
        return {
            "required_fields": required_fields,
            "required_severity": {},
            "type_expectations": type_expectations,
        }

    return {
        "required_fields": facility_schema.get(
            "required_fields", DEFAULT_SCHEMA["required_fields"]
        ),
        "required_severity": facility_schema.get(
            "required_severity", DEFAULT_SCHEMA["required_severity"]
        ),
        "type_expectations": facility_schema.get(
            "type_expectations", DEFAULT_SCHEMA["type_expectations"]
        ),
    }


def _normalize_schema_type(schema_type: str) -> str:
    mapping = {
        "array": "list",
        "object": "object",
        "string": "string",
        "number": "number",
        "integer": "number",
        "boolean": "boolean",
    }
    return mapping.get(schema_type, schema_type)


def _load_constraints_config(
    override: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    constraints_path = os.path.join(
        os.path.dirname(__file__),
        "constraints.json",
    )
    constraints = dict(DEFAULT_CONSTRAINTS)

    if os.path.exists(constraints_path):
        try:
            with open(constraints_path, "r", encoding="utf-8") as handle:
                file_config = json.load(handle)
            constraints = _merge_constraints(constraints, file_config)
        except (OSError, json.JSONDecodeError):
            pass

    if override:
        constraints = _merge_constraints(constraints, override)

    return constraints


def _merge_constraints(
    base: Dict[str, Any], override: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        merged[key] = value
    return merged


def _normalize_supply(supply_json: Dict[str, Any]) -> Dict[str, Any]:
    codes = sorted(_extract_codes(supply_json))
    negated_codes = sorted(_extract_negated_codes(supply_json))
    normalized = {
        "codes": codes,
        "canonical_capabilities": codes,
        "negated_codes": negated_codes,
        "evidence_index": supply_json.get("evidence_index") or {},
        "radiologist_count": _safe_number(supply_json.get("radiologist_count")),
        "anesthesia_staff": _safe_number(supply_json.get("anesthesia_staff")),
        "ventilators": _safe_number(supply_json.get("ventilators")),
        "critical_care_staff": _safe_number(supply_json.get("critical_care_staff")),
        "bed_count": _safe_number(supply_json.get("bed_count")),
        "staff_count": _safe_number(supply_json.get("staff_count")),
    }
    return normalized


def _safe_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _extract_codes(supply_json: Dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    canonical = supply_json.get("canonical_capabilities")
    if isinstance(canonical, list):
        for code in canonical:
            if isinstance(code, str) and code.strip():
                codes.add(code.strip())

    for key in ["capabilities", "equipment", "specialists"]:
        entries = supply_json.get(key) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            code = _entry_code(entry)
            if code:
                codes.add(code)
    return codes


def _extract_negated_codes(supply_json: Dict[str, Any]) -> set[str]:
    negated: set[str] = set()
    for key in ["capabilities", "equipment", "specialists"]:
        entries = supply_json.get(key) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("negated"):
                code = entry.get("capability_code") or _entry_code(entry)
                if code:
                    negated.add(str(code))
            elif hasattr(entry, "negated") and getattr(entry, "negated"):
                code = getattr(entry, "capability_code", None) or _entry_code(entry)
                if code:
                    negated.add(str(code))
    return negated


def _entry_code(entry: Any) -> Optional[str]:
    if isinstance(entry, dict):
        code = entry.get("capability_code")
        if code:
            return str(code)
        name = entry.get("name")
        if name:
            normalized = normalize_capability_name(str(name))
            return normalized.get("code")
    if hasattr(entry, "capability_code") and getattr(entry, "capability_code"):
        return str(getattr(entry, "capability_code"))
    normalized = normalize_capability_name(str(entry))
    return normalized.get("code")


def _run_schema_checks(
    supply_json: Dict[str, Any],
    schema_config: Dict[str, Any],
    issues: List[Issue],
    verdict: Literal["plausible", "suspicious", "impossible"],
) -> Literal["plausible", "suspicious", "impossible"]:
    required_fields = schema_config.get("required_fields", [])
    required_severity = schema_config.get("required_severity", {})
    type_expectations = schema_config.get("type_expectations", {})

    for field in required_fields:
        if supply_json.get(field) is None:
            severity = required_severity.get(field, "warning")
            verdict = _register_issue(
                issues,
                severity,
                "MISSING_REQUIRED_FIELD",
                f"Required field '{field}' is missing.",
                field,
                verdict,
                evidence=_extract_evidence(supply_json, field),
            )

    for field, expected_type in type_expectations.items():
        if field not in supply_json or supply_json.get(field) is None:
            continue
        if not _matches_type(supply_json.get(field), expected_type):
            verdict = _register_issue(
                issues,
                "error",
                "TYPE_MISMATCH",
                f"Field '{field}' should be type '{expected_type}'.",
                field,
                verdict,
                evidence=_extract_evidence(supply_json, field),
            )

    return verdict


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "list":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def _run_range_checks(
    supply_json: Dict[str, Any],
    issues: List[Issue],
    verdict: Literal["plausible", "suspicious", "impossible"],
) -> Literal["plausible", "suspicious", "impossible"]:
    for field in [
        "bed_count",
        "staff_count",
        "radiologist_count",
        "anesthesia_staff",
        "critical_care_staff",
    ]:
        if field in supply_json:
            value = supply_json.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                verdict = _register_issue(
                    issues,
                    "error",
                    "TYPE_MISMATCH",
                    f"Field '{field}' should be numeric.",
                    field,
                    verdict,
                    evidence=_extract_evidence(supply_json, field),
                )
            elif value < 0:
                verdict = _register_issue(
                    issues,
                    "error",
                    "RANGE_VIOLATION",
                    f"Field '{field}' must be >= 0.",
                    field,
                    verdict,
                    evidence=_extract_evidence(supply_json, field),
                )

    return verdict


def _run_constraint_checks(
    normalized: Dict[str, Any],
    constraints: Dict[str, Any],
    issues: List[Issue],
    verdict: Literal["plausible", "suspicious", "impossible"],
) -> Literal["plausible", "suspicious", "impossible"]:
    negated_codes = normalized.get("negated_codes", [])
    if negated_codes:
        codes = set(normalized.get("codes", []))
        for code in negated_codes:
            if code in codes:
                evidence = _evidence_for_codes(normalized, [code])
                verdict = _register_issue(
                    issues,
                    "error",
                    "CONTRADICTION_NEGATED_CLAIM",
                    f"Capability '{code}' is negated in evidence.",
                    "canonical_capabilities",
                    verdict,
                    evidence=evidence,
                )

    for rule in constraints.get("rules", []):
        if not _rule_triggered(rule, normalized):
            continue

        if _violates_rule(rule, normalized):
            severity = rule.get("severity", "warning")
            verdict_override = rule.get("verdict")
            evidence = _evidence_for_codes(
                normalized, (rule.get("when_any") or rule.get("when_all") or [])
            )
            verdict = _register_issue(
                issues,
                severity,
                rule.get("code", "CONSTRAINT_VIOLATION"),
                rule.get("message", "Constraint violated."),
                rule.get("path", "capabilities"),
                verdict,
                verdict_override=verdict_override,
                evidence=evidence,
            )

    return verdict


def _rule_triggered(rule: Dict[str, Any], normalized: Dict[str, Any]) -> bool:
    when_any = rule.get("when_any")
    when_all = rule.get("when_all")

    if when_any:
        return any(_truthy_key(normalized, key) for key in when_any)
    if when_all:
        return all(_truthy_key(normalized, key) for key in when_all)
    return True


def _violates_rule(rule: Dict[str, Any], normalized: Dict[str, Any]) -> bool:
    requires_any = rule.get("requires_any")
    requires_all = rule.get("requires_all")
    forbid_any = rule.get("forbid_any")
    forbid_all = rule.get("forbid_all")

    if requires_any and not any(_truthy_key(normalized, key) for key in requires_any):
        return True
    if requires_all and not all(_truthy_key(normalized, key) for key in requires_all):
        return True
    if forbid_any and any(_truthy_key(normalized, key) for key in forbid_any):
        return True
    if forbid_all and all(_truthy_key(normalized, key) for key in forbid_all):
        return True
    return False


def _run_confidence_checks(
    supply_json: Dict[str, Any],
    constraints: Dict[str, Any],
    issues: List[Issue],
    verdict: Literal["plausible", "suspicious", "impossible"],
) -> Literal["plausible", "suspicious", "impossible"]:
    threshold = constraints.get("confidence_threshold", 0.4)
    confidences = _collect_confidences(supply_json)

    for path, value in confidences:
        if value < threshold:
            verdict = _register_issue(
                issues,
                "warning",
                "LOW_CONFIDENCE_FIELD",
                f"Field '{path}' has low confidence ({value:.2f}).",
                path,
                verdict,
            )

    return verdict


def _collect_confidences(supply_json: Dict[str, Any]) -> List[Tuple[str, float]]:
    results: List[Tuple[str, float]] = []
    confidence_map = supply_json.get("confidence")
    if isinstance(confidence_map, dict):
        for key, value in confidence_map.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                results.append((f"confidence.{key}", float(value)))

    for key, value in supply_json.items():
        if isinstance(value, dict) and "confidence" in value:
            conf = value.get("confidence")
            if isinstance(conf, (int, float)) and not isinstance(conf, bool):
                results.append((key, float(conf)))

    return results


def _extract_evidence(
    supply_json: Dict[str, Any], field: str
) -> Optional[Dict[str, Any]]:
    evidence_map = supply_json.get("evidence")
    if isinstance(evidence_map, dict) and field in evidence_map:
        evidence = evidence_map.get(field)
        if isinstance(evidence, dict):
            return evidence
    field_value = supply_json.get(field)
    if isinstance(field_value, dict):
        evidence = field_value.get("evidence")
        if isinstance(evidence, dict):
            return evidence
    return None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return value is not None


def _truthy_key(normalized: Dict[str, Any], key: str) -> bool:
    if key in normalized:
        return _truthy(normalized.get(key))
    codes = normalized.get("codes", [])
    return key in set(codes)


def _evidence_for_codes(
    normalized: Dict[str, Any], codes: List[str]
) -> Optional[Dict[str, Any]]:
    evidence_index = normalized.get("evidence_index") or {}
    if not evidence_index:
        return None
    citation_ids: List[str] = []
    for code in codes:
        citation_ids.extend(find_evidence_for_code(code, evidence_index))
    citation_ids = list(dict.fromkeys(citation_ids))[:30]
    if not citation_ids:
        return None
    return {"citation_ids": citation_ids}


def _register_issue(
    issues: List[Issue],
    severity: str,
    code: str,
    message: str,
    path: str,
    verdict: Literal["plausible", "suspicious", "impossible"],
    verdict_override: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Literal["plausible", "suspicious", "impossible"]:
    issue = Issue(
        severity=severity,
        code=code,
        message=message,
        path=path,
        evidence=evidence,
    )
    issues.append(issue)

    return _update_verdict(verdict, severity, verdict_override)


def _update_verdict(
    current: Literal["plausible", "suspicious", "impossible"],
    severity: str,
    verdict_override: Optional[str],
) -> Literal["plausible", "suspicious", "impossible"]:
    if verdict_override in {"plausible", "suspicious", "impossible"}:
        return _max_verdict(current, verdict_override)

    if severity == "error":
        return _max_verdict(current, "impossible")
    if severity == "warning":
        return _max_verdict(current, "suspicious")
    return current


def _max_verdict(
    current: Literal["plausible", "suspicious", "impossible"],
    candidate: Literal["plausible", "suspicious", "impossible"],
) -> Literal["plausible", "suspicious", "impossible"]:
    order = {"plausible": 0, "suspicious": 1, "impossible": 2}
    return candidate if order[candidate] > order[current] else current


def _count_by_severity(issues: List[Issue]) -> Dict[str, int]:
    counts = {"info": 0, "warning": 0, "error": 0}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return counts


def _score_from_issues(issues: List[Issue]) -> float:
    score = 1.0
    for issue in issues:
        if issue.severity == "error":
            score -= 0.2
        elif issue.severity == "warning":
            score -= 0.1
        else:
            score -= 0.02
    return max(0.0, min(1.0, score))


def _build_explanation(
    verdict: str, issues: List[Issue]
) -> str:
    if verdict == "plausible":
        return "No blocking issues detected; supply looks plausible."
    if verdict == "suspicious":
        return "Supply has warnings that require review."
    if verdict == "impossible":
        return "Supply contains contradictions or hard violations."
    return "Validation completed."
