from __future__ import annotations

import json
import logging
import time
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.ai.orchestrator import MedicalOrchestrator
from backend.ai.rag.indexer import DocumentIndexer
from backend.config.runtime_paths import get_mlflow_dir, get_mlflow_tracking_uri
from src.ai.openai_client import DEFAULT_OPENAI_MODEL

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ai"])

MLFLOW_EXPERIMENT = "CancerCompass-Demo"
MLFLOW_DIR = get_mlflow_dir()

try:  # pragma: no cover - optional dependency
    import mlflow  # type: ignore
except Exception as exc:  # pragma: no cover - non-critical import
    mlflow = None
    logger.warning("MLflow import failed (non-critical): %s", exc)

if mlflow is not None:
    try:
        mlflow.set_tracking_uri(get_mlflow_tracking_uri())
        mlflow.set_experiment(MLFLOW_EXPERIMENT)
        logger.info("MLflow initialized at %s", MLFLOW_DIR)
    except Exception as exc:  # pragma: no cover - non-critical init
        logger.warning("MLflow initialization failed (non-critical): %s", exc)


class AskRequest(BaseModel):
    question: str
    context: Optional[str] = ""
    mode: Optional[str] = "rag"
    dataset_id: Optional[str] = None


class IndexRequest(BaseModel):
    dataset_id: str


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    dataset_id: Optional[str] = None


def _resolve_upload_path(dataset_id: str) -> Path | None:
    uploads_dir = Path("/app/backend/uploads")
    direct_path = uploads_dir / dataset_id
    if direct_path.exists():
        return direct_path
    candidates = list(uploads_dir.glob(f"{dataset_id}.*"))
    if candidates:
        return candidates[0]
    return None


@router.post("/ask")
async def ask_question(request: AskRequest) -> Dict:
    """Answer a medical question using RAG + orchestrator. Logs to MLflow."""
    start_time = time.time()
    dataset_id = request.dataset_id or ""

    try:
        orchestrator = MedicalOrchestrator(dataset_id=dataset_id or None)
        result = orchestrator.run(
            question=request.question,
            mode=request.mode or "rag",
            context=request.context or "",
        )
    except Exception as exc:
        logger.error("Ask endpoint failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    latency_ms = (time.time() - start_time) * 1000
    result["metadata"]["latency_ms"] = latency_ms

    if mlflow is not None:
        try:
            with mlflow.start_run(run_name=f"ask_{int(time.time())}"):
                mlflow.log_param("question", request.question[:100])
                mlflow.log_param("mode", request.mode)
                mlflow.log_param("model_name", DEFAULT_OPENAI_MODEL)
                if dataset_id:
                    mlflow.log_param("dataset_id", dataset_id)

                mlflow.log_metric("latency_ms", latency_ms)
                mlflow.log_metric("retrieved_chunks", len(result["sources"]))
                mlflow.log_metric("answer_length", len(result["answer"]))

                mlflow.set_tag("source", "orchestrator")
                mlflow.set_tag("databricks_ready", "true")

                if result["sources"]:
                    chunks_artifact = json.dumps(result["sources"], indent=2)
                    mlflow.log_text(chunks_artifact, "retrieved_chunks.json")
        except Exception as exc:  # pragma: no cover - non-critical logging
            logger.warning("MLflow logging failed (non-critical): %s", exc)

    return result


@router.post("/rag/index")
async def index_dataset(request: IndexRequest) -> Dict:
    """Index an uploaded dataset into the vector store."""
    dataset_path = _resolve_upload_path(request.dataset_id)
    if not dataset_path:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Dataset not found: {request.dataset_id}. "
                "Upload it first via /api/upload/dataset"
            ),
        )

    try:
        indexer = DocumentIndexer()
        result = indexer.index_file(str(dataset_path), request.dataset_id)
        logger.info("Indexed dataset: %s", result)
        return result
    except Exception as exc:
        logger.error("Indexing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/rag/query")
async def query_rag(request: QueryRequest) -> List[Dict]:
    """Query the RAG system directly for relevant chunks."""
    dataset_id = request.dataset_id or "default"
    try:
        indexer = DocumentIndexer()
        results = indexer.query(dataset_id=dataset_id, query=request.query, top_k=request.top_k or 5)
        return [
            {
                "chunk": result.get("text", ""),
                "score": result.get("_distance", 0.0),
                "metadata": {
                    "dataset_id": result.get("dataset_id"),
                    "chunk_index": result.get("chunk_index"),
                    "source": result.get("source"),
                },
            }
            for result in results
        ]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("RAG query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mlflow/recent")
async def get_recent_mlflow_runs(n: int = 20) -> List[Dict]:
    """Retrieve recent MLflow runs."""
    if mlflow is None:
        return []
    try:
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name(MLFLOW_EXPERIMENT)
        if not experiment:
            return []
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=n,
            order_by=["start_time DESC"],
        )
        return [
            {
                "run_id": run.info.run_id,
                "start_time": run.info.start_time,
                "params": run.data.params,
                "metrics": run.data.metrics,
                "tags": run.data.tags,
            }
            for run in runs
        ]
    except Exception as exc:
        logger.error("Failed to fetch MLflow runs: %s", exc, exc_info=True)
        return []
