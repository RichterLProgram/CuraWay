# Backend Layout

Top-level:
- `src/` – Backend-Code (features + pipelines)
- `scripts/` – ausführbare Einstiegspunkte
- `input/` – Demo-Inputs, getrennt nach Flows
- `output/` – erzeugte Outputs

Source structure:
- `src/features/` – Domänenmodule (patient, clinical_trials, idp, decision, aggregation, analyst, validation, explainability, ai, models)
- `src/pipelines/` – Pipeline-Orchestrierung und App-Pipelines

Inputs:
- `input/patient/` – Patient-Reports für CancerCompass
- `input/analyst/` – Facility-Dokumente + Demand-CSV für Analyst-Flow

Run:
```powershell
cd backend
python .\scripts\run_trial_matching.py
python .\scripts\run_analyst_view.py
```
