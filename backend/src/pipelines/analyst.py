"""Analyst flow pipeline (Medical Deserts + Demand)."""

from pathlib import Path
from typing import Set

from features.analyst.demand_loader import load_demand_points_csv, load_demand_points_json
from features.analyst.analytics import (
    build_facility_scorecards,
    compare_with_baseline,
    compute_decision_metrics,
    compute_snapshot,
    estimate_time_to_treatment,
    forecast_capacity_gaps,
    load_baseline,
    load_labels,
    simulate_roi,
)
from features.analyst.pipeline import build_analyst_api_data, build_analyst_map_data
from features.analyst.validation import (
    RAGIndex,
    build_cross_source_report,
    build_review_queue,
    load_external_sources,
)
from features.explainability.provenance import build_pipeline_trace
from features.explainability.mlflow_tracking import log_pipeline_result
from features.idp.llm_extractors import load_llm_extractor
from io_utils import load_documents, write_json
from pipelines.orchestration import run_pipeline


def run_analyst_pipeline(
    input_dir: Path,
    output_dir: Path,
    demand_csv: Path,
    demand_patient_json: Path,
    skip_names: Set[str],
) -> object:
    documents = load_documents(input_dir, skip_names=skip_names)
    pipeline_result = run_pipeline(documents, llm_extractor=load_llm_extractor())

    log_pipeline_result(pipeline_result, run_name="analyst_pipeline")

    demand_points = load_demand_points_csv(demand_csv)
    patient_points = load_demand_points_json(demand_patient_json)
    merged_points = _merge_demand_points(demand_points + patient_points)

    analyst_map = build_analyst_map_data(pipeline_result.regional_assessments, merged_points)
    impact_kpis = estimate_time_to_treatment(pipeline_result.regional_assessments, merged_points)
    capacity_forecast = forecast_capacity_gaps(pipeline_result.regional_assessments, merged_points)
    roi_simulation = simulate_roi(pipeline_result.regional_assessments, merged_points)

    labels = load_labels(input_dir / "labels.json")
    benchmark_metrics = (
        compute_decision_metrics(pipeline_result.capability_decisions, labels)
        if labels
        else None
    )

    meta = {
        "demand_sources": ["csv", "patient_matching"],
        "impact_kpis": impact_kpis,
        "capacity_forecast": capacity_forecast,
        "roi_simulation": roi_simulation,
    }
    if benchmark_metrics:
        meta["benchmark_metrics"] = benchmark_metrics
    analyst_api = build_analyst_api_data(
        pipeline_result.regional_assessments,
        merged_points,
        meta=meta,
    )
    pipeline_trace = build_pipeline_trace(pipeline_result)

    scorecards = build_facility_scorecards(pipeline_result)
    review_queue = build_review_queue(pipeline_result.capability_decisions)
    monitoring_snapshot = compute_snapshot(pipeline_result)
    baseline = load_baseline(output_dir / "monitoring_baseline.json")
    monitoring_drift = (
        compare_with_baseline(monitoring_snapshot, baseline)
        if baseline
        else {"drift_detected": False, "note": "no baseline found"}
    )

    external_sources = []
    external_sources += load_external_sources(input_dir / "external_sources")
    external_sources += load_external_sources(input_dir.parent / "external_sources")
    cross_source_report = None
    if external_sources:
        rag_index = RAGIndex.from_documents(external_sources, source="external_sources")
        cross_source_report = build_cross_source_report(
            pipeline_result.capability_decisions, rag_index
        )

    output_dir.mkdir(exist_ok=True)
    write_json(output_dir / "analyst_map_data.json", analyst_map.model_dump())
    write_json(output_dir / "analyst_api.json", analyst_api.model_dump())
    write_json(output_dir / "analyst_trace.json", analyst_map.trace.model_dump())
    write_json(output_dir / "pipeline_trace.json", pipeline_trace.model_dump())
    write_json(output_dir / "facility_scorecards.json", scorecards)
    write_json(output_dir / "review_queue.json", review_queue)
    write_json(output_dir / "monitoring_snapshot.json", monitoring_snapshot)
    write_json(output_dir / "monitoring_drift.json", monitoring_drift)
    write_json(output_dir / "impact_kpis.json", impact_kpis)
    write_json(output_dir / "capacity_forecast.json", capacity_forecast)
    write_json(output_dir / "roi_simulation.json", roi_simulation)
    if benchmark_metrics:
        write_json(output_dir / "benchmark_metrics.json", benchmark_metrics)
    if cross_source_report:
        write_json(output_dir / "cross_source_report.json", cross_source_report)
    return analyst_api


def _merge_demand_points(points):
    seen = set()
    merged = []
    for p in points:
        key = (round(p.latitude, 4), round(p.longitude, 4), p.label.lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append(p)
    return merged
