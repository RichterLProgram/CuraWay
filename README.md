# CancerCompass

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
