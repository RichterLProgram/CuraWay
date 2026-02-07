# Orchestration Status (English Summary)

## What this covers
- Linear IDP → decision → aggregation pipeline
- Evidence normalization and provenance handling

## Current status
- Pipeline runs end-to-end with deterministic outputs
- Evidence is enriched with document and chunk IDs
- Regional aggregation produces risk scores

## Next steps (optional)
- Add timed trace for each pipeline stage
- Expand aggregation with geospatial weighting
# Statusbericht: Orchestration, Models, Aggregation

**Datum:** 7. Februar 2025  
**Getestet:** `orchestration/`, `models/`, `aggregation/`

---

## Kurzfassung

- **43 Tests** (21 idp/decision + 22 orchestration/models/aggregation) laufen erfolgreich.
- **Ein Fix** wurde durchgeführt: `medical_desert_assessor.py` nutzte noch `.dict()` → `.model_dump()`.
- **Keine weiteren Bugs** gefunden.

---

## 1. Neue Test-Suites

### models/shared.py → `test_models_shared.py`

| Modell | Tests |
|--------|-------|
| EvidenceSnippet | valid, empty_text_fails, empty_document_id_fails |
| CapabilityDecision | valid |
| RegionalRiskLevel | levels, invalid_level_fails |
| FacilityWithCapabilityDecisions | valid, empty_facility_id_fails |
| RegionalAssessment | valid |

### aggregation/medical_desert_assessor.py → `test_aggregation.py`

| Szenario | Test |
|----------|------|
| Hohes Risiko | Region ohne Capabilities → risk_level="high" |
| Niedriges Risiko | Region mit 6/6 Capabilities → risk_level="low" |
| Mittleres Risiko | Region mit 2/6 Capabilities → risk_level="medium" |
| Gruppierung | Mehrere Facilities pro Region → korrekte Aggregation |

### orchestration/ → `test_orchestration.py`

| Bereich | Tests |
|---------|-------|
| Pipeline | run_pipeline_raw_text, run_pipeline_pre_extracted |
| Provenance | evidence_provenance_enriched |
| Validierung | pre_extracted_string_evidence_fails |
| IDP-Parsing | try_parse_idp_payload_valid, try_parse_idp_payload_invalid |
| Trace | build_pipeline_trace |
| Evidence-Normalisierung | normalize_evidence_skips_unknown, normalize_evidence_preserves_provenance |

---

## 2. Behobener Fix

### Pydantic v2: `.dict()` in medical_desert_assessor.py

**Ort:** Zeile 147, `if __name__ == "__main__"`

**Problem:** `[r.dict() for r in result]` – Pydantic v2 nutzt `.model_dump()`.

**Fix:**
```python
print(json.dumps([r.model_dump() for r in result], indent=2))
```

---

## 3. Status pro Modul

### orchestration/pipeline.py

- `run_pipeline(documents, llm_extractor)` – erfordert LLM-Extractor für Raw-Text
- Pre-extracted JSON mit Evidence-Provenance (document_id, chunk_id) wird validiert
- String-Evidence ohne Provenance führt zu `ValueError`
- Evidence wird mit `document_id` und `chunk_id` angereichert

### orchestration/trace.py

- `build_pipeline_trace(pipeline_result)` – baut Audit-Trace
- Evidence ohne Provenance wird übersprungen (nicht mit "unknown" normalisiert)
- Verwendet `model_dump()` (Pydantic v2)

### models/shared.py

- EvidenceSnippet, CapabilityDecision, RegionalRiskLevel, FacilityWithCapabilityDecisions, RegionalAssessment
- Validierung funktioniert (min_length, Literal)

### aggregation/medical_desert_assessor.py

- `assess_medical_desert(facilities)` – gruppiert nach Region, bewertet Risiko
- Risiko-Schwellen: high (<2), medium (<4), low (≥4) essentielle Capabilities
- Keine LLM-Aufrufe, deterministisch

---

## 4. Test-Ausführung

```bash
cd backend
$env:PYTHONPATH = "."   # PowerShell
python -m pytest test/ -v
```

**Ergebnis:** 43 passed

---

## 5. Empfehlungen

1. **requirements.txt** anlegen mit: `pydantic>=2.0`, `typing_extensions`, `pytest`
2. **CI/CD** – pytest bei jedem Commit ausführen
3. **Demo-Skript** – zentrales Skript für End-to-End-Demo (Pipeline + Trace)
