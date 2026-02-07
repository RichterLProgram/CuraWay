"""Optional MLflow tracking for pipeline runs."""

import os
from collections import Counter
from typing import Any


def log_pipeline_result(pipeline_result: Any, run_name: str = "idp_pipeline") -> None:
    if os.getenv("MLFLOW_ENABLED", "0") not in {"1", "true", "yes"}:
        return
    try:
        import mlflow
    except Exception:
        return

    mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "CancerCompass"))
    with mlflow.start_run(run_name=run_name):
        facility_count = len(pipeline_result.capability_decisions)
        region_count = len(pipeline_result.regional_assessments)
        mlflow.log_metric("facility_count", facility_count)
        mlflow.log_metric("region_count", region_count)

        risk_counts = Counter([a.risk_level.level for a in pipeline_result.regional_assessments])
        for level, count in risk_counts.items():
            mlflow.log_metric(f"risk_{level}_count", count)

        coverage_scores = [a.coverage_score for a in pipeline_result.regional_assessments]
        if coverage_scores:
            mlflow.log_metric("coverage_avg", sum(coverage_scores) / len(coverage_scores))
