# Analyse: RAG + Orchestrator + MLflow Integration

## Einstiegspunkt der Anwendung
- Datei: `backend/api/server.py`
- FastAPI-App: `fastapi_app = FastAPI()` und am Ende `app = fastapi_app`.
- Flask-App: `app = Flask(__name__)` wird als WSGI unter `/api` gemountet:
  - `fastapi_app.mount("/api", WSGIMiddleware(app))`
- Statische Dateien:
  - `STATIC_DIR = .../backend/static`
  - Root-Route `/` liefert `index.html` oder Debug-JSON
  - `fastapi_app.mount("/", StaticFiles(...), name="static")` wenn `STATIC_DIR` existiert

## Upload-Endpoint
- Route: `POST /api/upload/dataset` in `backend/api/server.py` (FastAPI).
- Speicherpfad: `uploads_dir = Path("/app/backend/uploads")`
- Dateiname: `uuid.uuid4().hex` + Dateiendung, Response enthält `filename`.
- Beispiel: `/app/backend/uploads/<uuid>.<ext>`

## LLM-Client
- Importpfad: `backend/src/ai/llm_client.py`
- Funktionssignatur: `call_llm(prompt, schema=None, temperature=None, model=None, system_prompt=None, trace_id=None, ...)`
- Modellkonfiguration:
  - Default OpenAI Modell: `DEFAULT_OPENAI_MODEL` in `backend/src/ai/openai_client.py` (Default: `gpt-4o-mini`)
  - Provider über `LLM_PROVIDER` (openai/claude), Fallbacks/Mocks über `LLM_DISABLED`
- Rückgabe: `LlmResult(text, parsed, model, provider, usage, latency_ms)`

## Konfigurationsmuster
- Kein zentrales Settings-Modul gefunden.
- Konfiguration über `os.getenv(...)` in Modulen (z.B. `llm_client.py`, `openai_client.py`).
- Optionaler Key über Datei: `OPENAI_API_KEY_FILE`.

## Docker/Render Setup
- Dockerfile:
  - Arbeitsverzeichnis: `/app`
  - `PYTHONPATH="/app/backend"`
  - Backend läuft via `uvicorn backend.api.server:app`
- Schreibpfade:
  - Uploads: `/app/backend/uploads`
  - Geplante neue Pfade (sollten schreibbar sein): `/app/backend/data/`, `/app/backend/mlruns`

## Dependencies
- Datei: `backend/requirements.txt`
- Vorhanden: `fastapi`, `flask`, `uvicorn[standard]`, `pydantic`, `openai`, `anthropic`, usw.
- Neue Abhaengigkeiten muessen hier additiv ergaenzt werden.
