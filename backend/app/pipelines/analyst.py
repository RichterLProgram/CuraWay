"""Analyst flow pipeline (Medical Deserts + Demand)."""

from pathlib import Path
from typing import Set

from analyst.demand_loader import load_demand_points_csv, load_demand_points_json
from analyst.pipeline import build_analyst_api_data, build_analyst_map_data
from app.io import load_documents, write_json
from orchestration.pipeline import _demo_llm_extractor, run_pipeline


def run_analyst_pipeline(
    input_dir: Path,
    output_dir: Path,
    demand_csv: Path,
    demand_patient_json: Path,
    skip_names: Set[str],
) -> object:
    documents = load_documents(input_dir, skip_names=skip_names)
    pipeline_result = run_pipeline(documents, llm_extractor=_demo_llm_extractor)

    demand_points = load_demand_points_csv(demand_csv)
    patient_points = load_demand_points_json(demand_patient_json)
    merged_points = _merge_demand_points(demand_points + patient_points)

    analyst_map = build_analyst_map_data(pipeline_result.regional_assessments, merged_points)
    analyst_api = build_analyst_api_data(
        pipeline_result.regional_assessments,
        merged_points,
        meta={"demand_sources": ["csv", "patient_matching"]},
    )

    output_dir.mkdir(exist_ok=True)
    write_json(output_dir / "analyst_map_data.json", analyst_map.model_dump())
    write_json(output_dir / "analyst_api.json", analyst_api.model_dump())
    write_json(output_dir / "analyst_trace.json", analyst_map.trace.model_dump())
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
