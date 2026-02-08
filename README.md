# CancerCompass

## Render Deploy (Docker)

- Deploy on Render as Docker Web Service
- Custom Domain zeigt auf denselben Service (eine Domain)
- API liegt unter `/api`
- Frontend wird vom Backend als Static Build ausgeliefert

Kurzcheck:
- Render: Language `Docker`, kein Start Command nötig
- Env Vars: `LLM_DISABLED=true` (optional für deterministische Tests)

## ✨ Latest Updates - Hotspot Report Feature (FIXED!)

Der "Take Action" Button funktioniert jetzt vollständig! 
- ✅ AI-generierte Berichte für ausgewählte Hotspots
- ✅ Automatische Simulation mit verschiedenen Szenarien
- ✅ Personalisierte Empfehlungen basierend auf Gap-Analyse
- ✅ RAG-Integration für evidenzbasierte Vorschläge

**Alle Details zu den Bugfixes:** siehe [BUGFIXES.md](./BUGFIXES.md)

---

## Quick Start

### 1) Patient Flow (CancerCompass)
Run clinical trial matching from reports in `backend/input/`.

```powershell
cd backend
python run_trial_matching.py
```

Outputs (in `backend/output/`):
- `trial_matching_result.json`
- `trial_matching_top3.json`
- `trial_matching_trace.json`
- `patient_api.json`
- `demand_points_from_patients.json`

### 2) Analyst Flow (Medical Deserts)
Run capability extraction and desert mapping from facility docs in `backend/input/analyst/`.

```powershell
cd backend
python run_analyst_view.py
```

Outputs:
- `analyst_map_data.json`
- `analyst_api.json`
- `analyst_trace.json`

### 3) Unified Bundle (Tabs + KPIs)
Run both flows and write a unified frontend shell.

```powershell
cd backend
python run_app_bundle.py
```

Outputs:
- `app_shell.json`

## Agent API (FastAPI)

Run the agent service (FastAPI) on port 8000:

```powershell
cd backend
uvicorn agent_api.main:app --reload --port 8000
```

Build or refresh the RAG index:

```powershell
cd backend
python .\scripts\build_rag_index.py
```

Databricks Vector Search (optional):
- Set `DATABRICKS_HOST` and `DATABRICKS_TOKEN`
- Set `DATABRICKS_VECTOR_SEARCH_ENDPOINT`
- Set `DATABRICKS_VECTOR_SEARCH_INDEX`
Databricks SQL (optional): `pip install -r backend/requirements-databricks.txt`

Text2SQL (Genie-style) endpoint:

```powershell
curl -X POST http://localhost:8000/agent/text2sql `
  -H "Content-Type: application/json" `
  -d '{\"question\":\"Count facilities by region\",\"schema\":\"facilities(id, name, region)\"}'
```

## Supply Validation API

Validate supply output against schema + constraints:

```powershell
curl -X POST http://localhost:5000/validate/supply `
  -H "Content-Type: application/json" `
  -d '{\"supply\":{\"facility_id\":\"fac-001\",\"name\":\"Example Hospital\",\"location\":{\"lat\":5.6,\"lng\":-0.1,\"region\":\"Accra\"},\"capabilities\":[\"CT scan\"],\"equipment\":[],\"specialists\":[],\"coverage_score\":80}}'
```

## Planner API

Generate action cards based on demand/supply:

```powershell
curl -X POST http://localhost:5000/planner/plan `
  -H "Content-Type: application/json" `
  -d '{\"demand\":{\"diagnosis\":\"lung cancer\",\"stage\":\"IV\",\"location\":{\"lat\":5.6,\"lon\":-0.1,\"region\":\"Greater Accra\"},\"urgency\":8,\"required_capabilities\":[\"ONC_GENERAL\",\"IMAGING_CT\"]},\"supply\":[]}'
```

## Facility Answer API

Answer if a facility can cover required capabilities:

```powershell
curl -X POST http://localhost:5000/facility/answer `
  -H "Content-Type: application/json" `
  -d '{\"facility_id\":\"F-1\",\"required_capability_codes\":[\"IMAGING_CT\"],\"facility\":{\"facility_id\":\"F-1\",\"canonical_capabilities\":[\"IMAGING_CT\"]}}'
```

## Desert Analytics API

Rank top deserts from demand/supply:

```powershell
curl -X POST http://localhost:5000/analytics/deserts `
  -H "Content-Type: application/json" `
  -d '{\"demands\":[{\"diagnosis\":\"lung cancer\",\"location\":{\"lat\":5.6,\"lon\":-0.1,\"region\":\"Greater Accra\"},\"urgency\":8,\"required_capabilities\":[\"IMAGING_CT\"]}],\"supply\":[]}'
```

## Desert Score API (Deterministic)

Quantify medical deserts for a specific capability target:

```powershell
curl -X POST http://localhost:5000/analytics/deserts/score `
  -H "Content-Type: application/json" `
  -d '{\"capability_target\":\"IMAGING_CT\",\"region\":{\"lat\":5.6,\"lon\":-0.1,\"radius_km\":200},\"facilities\":[]}'
```

### Environment

- `LLM_DISABLED=true` uses fixtures for deterministic tests.
- `MLFLOW_ENABLED=true` enables MLflow export (optional).

## Planner Engine API

Structured planning response for the dashboard:

```powershell
curl -X GET http://localhost:5000/data/planner_engine
```

Custom payload:

```powershell
curl -X POST http://localhost:5000/planner/engine `
  -H "Content-Type: application/json" `
  -d '{\"region\":\"North\",\"hotspots\":[],\"baseline_kpis\":{}}'
```

## Trace Debug API

Fetch step-level trace events:

```powershell
curl http://localhost:5000/trace/<trace_id>
```

Fetch trace summary:

```powershell
curl http://localhost:5000/trace/<trace_id>/summary
```

### 3b) Unified Workflow (Flows + Analytics)
Run both flows and write all analytics outputs in one command.

```powershell
cd backend
python .\scripts\run_unified_workflow.py
```

Optional env:
- `SAVE_MONITORING_BASELINE=1` → writes `monitoring_baseline.json`
- `COPY_FRONTEND_ASSETS=1` → copies `backend/output` to `frontend/public/data`

### 4) Facility IDP Pipeline (VF Track)
Run the facility parsing pipeline directly.

```powershell
cd backend
python run_from_input.py
```

Output:
- `pipeline_result.json`
"# CancerCompass

## Medical Reports verarbeiten

1. **Medical Reports ablegen** im Verzeichnis `backend/input/`:
   - Immer: `.txt`, `.json`, `.csv`, `.md`, `.rtf`, `.xml`
   - Optional (pip install): `.docx`, `.xlsx`, `.xls`, `.pdf`, `.odt`

2. **Pipeline ausführen** (im Projekt-Root oder in `backend/`):

   ```powershell
   cd backend
   $env:PYTHONPATH="."
   python run_from_input.py
   ```

   Oder in einer Zeile:

   ```powershell
   cd c:\Users\shawn\CancerCompass\backend; $env:PYTHONPATH="."; python run_from_input.py
   ```

3. **Ergebnis:** Die Ausgabe erscheint in der Konsole und wird zusätzlich in `backend/output/pipeline_result.json` gespeichert." 
