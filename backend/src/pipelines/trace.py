"""Re-export from explainability.provenance for backwards compatibility."""

from features.explainability.provenance import (
    TraceEvidenceSnippet,
    build_pipeline_trace,
    PipelineTrace,
    _normalize_evidence,
)

__all__ = ["build_pipeline_trace", "PipelineTrace", "TraceEvidenceSnippet", "_normalize_evidence"]
