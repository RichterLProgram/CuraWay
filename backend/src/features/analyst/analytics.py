"""Analytics helpers for the Analyst flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


_ESSENTIAL = [
    "oncology_services",
    "ct_scanner",
    "mri_scanner",
    "pathology_lab",
    "chemotherapy_delivery",
    "icu",
]

_CAPEX = {
    "oncology_services": 400_000,
    "ct_scanner": 900_000,
    "mri_scanner": 1_200_000,
    "pathology_lab": 350_000,
    "chemotherapy_delivery": 250_000,
    "radiotherapy": 2_500_000,
    "icu": 600_000,
    "trial_coordinator": 120_000,
}


def build_facility_scorecards(pipeline_result) -> List[dict]:
    cards: List[dict] = []
    regions = _facility_regions(pipeline_result.raw_idp_output)
    for idx, (facility_id, decisions) in enumerate(
        pipeline_result.capability_decisions.items(), start=1
    ):
        confirmed = []
        missing = []
        evidence_count = 0
        confidence_sum = 0.0
        for cap in _ESSENTIAL:
            decision = decisions.get(cap, {})
            if decision.get("decision_reason") == "direct_evidence" and decision.get("value") is True:
                confirmed.append(cap)
            else:
                missing.append(cap)
            evidence = decision.get("evidence", []) or []
            evidence_count += len(evidence)
            confidence_sum += float(decision.get("confidence", 0.0) or 0.0)

        score = round(len(confirmed) / len(_ESSENTIAL), 3)
        confidence_avg = round(confidence_sum / max(len(_ESSENTIAL), 1), 3)
        cards.append(
            {
                "facility_id": facility_id,
                "region": regions.get(idx, "unknown"),
                "confirmed_capabilities": confirmed,
                "missing_capabilities": missing,
                "coverage_score": score,
                "evidence_count": evidence_count,
                "confidence_avg": confidence_avg,
            }
        )
    return cards


def estimate_time_to_treatment(
    regional_assessments: List[object],
    demand_points: List[object],
    baseline_days: int = 120,
) -> dict:
    if not regional_assessments:
        return {
            "baseline_days": baseline_days,
            "estimated_days": baseline_days,
            "reduction_ratio": 0.0,
            "regions": [],
        }

    region_weights = _demand_weights(regional_assessments, demand_points)
    weighted_days = 0.0
    total_weight = 0.0
    region_kpis = []
    for assessment in regional_assessments:
        coverage = float(assessment.coverage_score)
        adjusted_days = max(30.0, baseline_days * (1.1 - coverage))
        weight = region_weights.get(assessment.region, 1.0)
        weighted_days += adjusted_days * weight
        total_weight += weight
        region_kpis.append(
            {
                "region": assessment.region,
                "coverage_score": coverage,
                "estimated_days": round(adjusted_days, 1),
                "weight": weight,
                "risk_level": assessment.risk_level.level,
            }
        )
    estimated_days = weighted_days / total_weight if total_weight else baseline_days
    reduction_ratio = max(0.0, (baseline_days - estimated_days) / baseline_days)
    return {
        "baseline_days": baseline_days,
        "estimated_days": round(estimated_days, 1),
        "reduction_ratio": round(reduction_ratio, 3),
        "regions": region_kpis,
    }


def simulate_roi(
    regional_assessments: List[object],
    demand_points: List[object],
) -> List[dict]:
    demand_weights = _demand_weights(regional_assessments, demand_points)
    results = []
    for region in regional_assessments:
        missing = region.missing_capabilities or []
        capex = sum(_CAPEX.get(cap, 200_000) for cap in missing)
        weight = demand_weights.get(region.region, 1.0)
        impact_score = weight * (1.0 + (1.0 - region.coverage_score))
        roi_index = round((impact_score / max(capex, 1.0)) * 1_000_000, 4)
        results.append(
            {
                "region": region.region,
                "missing_capabilities": missing,
                "capex_estimate_usd": int(capex),
                "impact_score": round(impact_score, 3),
                "roi_index": roi_index,
                "risk_level": region.risk_level.level,
            }
        )
    return results


def forecast_capacity_gaps(
    regional_assessments: List[object],
    demand_points: List[object],
) -> List[dict]:
    demand_by_region = _map_demand_to_regions(regional_assessments, demand_points)
    forecasts: List[dict] = []
    for region in regional_assessments:
        demand = demand_by_region.get(region.region, 0)
        coverage = float(region.coverage_score)
        gap_index = round(demand * (1.0 - coverage), 3)
        forecasts.append(
            {
                "region": region.region,
                "demand_points": demand,
                "coverage_score": coverage,
                "gap_index": gap_index,
                "priority": _priority(gap_index, region.risk_level.level),
            }
        )
    return forecasts


def compute_snapshot(
    pipeline_result,
) -> Dict[str, object]:
    decision_reasons: Dict[str, int] = {}
    missing_evidence = 0
    evidence_total = 0
    suspicious_claims = 0

    for output in pipeline_result.raw_idp_output:
        if isinstance(output, dict):
            metadata = output.get("metadata", {}) or {}
            suspicious_claims += len(metadata.get("suspicious_claims", []) or [])

    for _, decisions in pipeline_result.capability_decisions.items():
        for _, decision in decisions.items():
            reason = decision.get("decision_reason", "insufficient_evidence")
            decision_reasons[reason] = decision_reasons.get(reason, 0) + 1
            evidence = decision.get("evidence", []) or []
            evidence_total += 1
            if not evidence:
                missing_evidence += 1

    evidence_missing_rate = (
        round(missing_evidence / evidence_total, 4) if evidence_total else 0.0
    )
    return {
        "facility_count": len(pipeline_result.capability_decisions),
        "region_count": len(pipeline_result.regional_assessments),
        "evidence_missing_rate": evidence_missing_rate,
        "evidence_missing_count": missing_evidence,
        "decision_reasons": decision_reasons,
        "suspicious_claims": suspicious_claims,
    }


def compare_with_baseline(
    snapshot: Dict[str, object],
    baseline: Dict[str, object],
    delta_threshold: float = 0.2,
) -> Dict[str, object]:
    def _delta(key: str) -> float:
        return float(snapshot.get(key, 0.0)) - float(baseline.get(key, 0.0))

    evidence_delta = _delta("evidence_missing_rate")
    suspicious_delta = _delta("suspicious_claims")
    return {
        "drift_detected": (
            abs(evidence_delta) >= delta_threshold
            or abs(suspicious_delta) >= delta_threshold
        ),
        "evidence_missing_rate_delta": round(evidence_delta, 4),
        "suspicious_claims_delta": round(suspicious_delta, 4),
    }


def load_baseline(path: Path) -> Optional[Dict[str, object]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_baseline(path: Path, snapshot: Dict[str, object]) -> None:
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")


def load_labels(path: Path) -> Optional[List[dict]]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def compute_decision_metrics(
    capability_decisions: Dict[str, Dict[str, dict]],
    labels: List[dict],
) -> Dict[str, object]:
    y_true = []
    y_pred = []
    for item in labels:
        facility_id = item.get("facility_id")
        capability = item.get("capability")
        label = bool(item.get("label"))
        decisions = capability_decisions.get(facility_id, {})
        if capability not in decisions:
            continue
        pred = bool(decisions[capability].get("value"))
        y_true.append(label)
        y_pred.append(pred)
    return _binary_metrics(y_true, y_pred)


def _binary_metrics(y_true: List[bool], y_pred: List[bool]) -> Dict[str, object]:
    if not y_true:
        return {"samples": 0, "precision": None, "recall": None, "false_positive_rate": None}
    tp = sum(1 for t, p in zip(y_true, y_pred) if t and p)
    fp = sum(1 for t, p in zip(y_true, y_pred) if not t and p)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t and not p)
    tn = sum(1 for t, p in zip(y_true, y_pred) if not t and not p)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "samples": len(y_true),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "false_positive_rate": round(fpr, 3),
    }


def _facility_regions(raw_outputs: List[dict]) -> Dict[int, str]:
    regions: Dict[int, str] = {}
    for idx, output in enumerate(raw_outputs, start=1):
        if isinstance(output, dict):
            region = output.get("facility_info", {}).get("region")
            regions[idx] = region or "unknown"
    return regions


def _demand_weights(regional_assessments: List[object], demand_points: List[object]) -> dict:
    weights = {a.region: 1.0 for a in regional_assessments}
    if not demand_points:
        return weights
    for point in demand_points:
        label = getattr(point, "label", "") or ""
        for region in weights.keys():
            if region.lower() in label.lower():
                weights[region] += 1.0
                break
    return weights


def _map_demand_to_regions(regional_assessments: List[object], demand_points: List[object]) -> dict:
    counts = {region.region: 0 for region in regional_assessments}
    if not demand_points:
        return counts
    for point in demand_points:
        label = getattr(point, "label", "") or ""
        matched = False
        for region in counts.keys():
            if region.lower() in label.lower():
                counts[region] += 1
                matched = True
                break
        if not matched and "unknown" in counts:
            counts["unknown"] += 1
    return counts


def _priority(gap_index: float, risk_level: str) -> str:
    if risk_level == "high" or gap_index >= 3.0:
        return "urgent"
    if risk_level == "medium" or gap_index >= 1.5:
        return "high"
    return "moderate"
