# RAG + Agentic Orchestration Demo

## Features Implemented

- RAG system with LanceDB vector storage
- LangGraph-based orchestrator (Retrieve -> Generate -> Validate)
- MLflow experiment tracking
- Medical safety validator (heuristic)
- Databricks-ready scaffold (requires env vars to activate)

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the server
```bash
uvicorn backend.api.server:app --host 0.0.0.0 --port 8000
```
On Render, set `APP_DATA_DIR=/tmp/cancercompass` (default) or mount a disk and set `APP_DATA_DIR=/opt/data`.

### 3. Upload a dataset
```bash
curl -X POST http://localhost:8000/api/upload/dataset \
  -F "file=@medical_doc.txt"
```

Response includes `filename` (use this as `dataset_id` in the next step).

### 4. Index the dataset
```bash
curl -X POST http://localhost:8000/api/rag/index \
  -H "Content-Type: application/json" \
  -d '{"dataset_id":"<filename_from_upload>"}'
```

### 5. Ask questions
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is immunotherapy?","mode":"rag","dataset_id":"<filename_from_upload>"}'
```

### 6. View MLflow runs
```bash
curl "http://localhost:8000/api/mlflow/recent?n=5"
```

## Databricks Integration

To enable Databricks features, set:
```bash
export DATABRICKS_HOST=your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-token
export DATABRICKS_SQL_WAREHOUSE_ID=your-warehouse-id
```

Without these, the system runs fully locally with LanceDB.

## Architecture

- Orchestrator: LangGraph (graph-based workflow)
- Vector Store: LanceDB (persistent, local)
- Tracking: MLflow (file-based, `./backend/mlruns`)
- Safety: Heuristic validator for medical content
