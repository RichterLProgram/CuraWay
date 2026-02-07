# Key Learnings (English Summary)

- Evidence + provenance are critical for auditability
- Conservative decisions avoid overclaiming capabilities
- Aggregation should be deterministic and explainable
- Demand signals help prioritize resource allocation
# Test-Erkenntnisse: backend/idp

**Datum:** 7. Februar 2025  
**Getestet:** `idp/extraction_agent.py` – IDP-Agent für Extraktion von Klinik-Kapazitäten aus unstrukturiertem Text

---

## Kurzfassung

- **21 Unit-Tests** wurden angelegt und laufen erfolgreich.
- **Ein Bug** wurde behoben (`root_validator` ohne `skip_on_failure=True`).
- **Pydantic v2 Migration** wurde vollständig durchgeführt.
- **Ein funktionaler Bug** im `__main__`-Block wurde behoben (siehe unten).

---

## 1. Behobener Bug

### Pydantic v2: `root_validator` ohne `skip_on_failure=True`

**Ort:** Zeile 54, `CapabilitySchema.validate_alignment`

**Problem:** Unter Pydantic v2 schlagen `root_validator`-Decoratoren ohne `skip_on_failure=True` mit einem Fehler fehl.

**Behobene Änderung:**
```python
@root_validator(skip_on_failure=True)
def validate_alignment(cls, values: Dict) -> Dict:
```

---

## 2. Bugs und Probleme (noch offen)

### 2.1 Demo-Block (`if __name__ == "__main__"`) – behoben

**Ort:** Zeile 486

**Problem (gelöst):** `parsed.json(indent=2)` – in Pydantic v2 unterstützt `.json()` keine Argumente wie `indent=2`.

**Fix (angewendet):**
```python
print(parsed.model_dump_json(indent=2))
```
Analoge Anpassung für `v.dict()` → `v.model_dump()` in Zeile 488.

---

### 2.2 Pydantic v1 → v2 Migration – erledigt

Alle folgenden Stellen wurden auf Pydantic v2 umgestellt:

| Ort | Vorher (v1) | Nachher (v2) |
|-----|-------------|--------------|
| Import | `root_validator, validator` | `field_validator, model_validator` |
| Metadata | `@validator("confidence_scores")` | `@field_validator("confidence_scores")` |
| CapabilitySchema | `@root_validator` | `@model_validator(mode="before")` |
| validate_alignment | `capabilities.dict()` | `capabilities.model_dump()` (falls Modell) |
| _aggregate_capabilities | `Capabilities.__fields__` | `Capabilities.model_fields` |
| build_capability_decisions | `capabilities.dict()` | `capabilities.model_dump()` |
| Demo-Block | `.json()`, `v.dict()` | `model_dump_json()`, `v.model_dump()` |

Keine Deprecation-Warnungen mehr.

---

### 2.3 Potentieller Bug: `value` als String

**Ort:** Zeile 228, `_aggregate_capabilities`

**Problem:** Wenn das LLM `"value": "false"` (String) statt `false` (Boolean) zurückgibt, liefert `bool("false")` `True`, weil jeder nicht-leere String truthy ist. Dadurch würden Capabilities fälschlicherweise auf `True` gesetzt.

**Aktueller Code:**
```python
cap_value = bool(cap.get("value", False))
```

**Empfohlener Fix:**
```python
raw_val = cap.get("value", False)
cap_value = raw_val is True or (isinstance(raw_val, str) and raw_val.lower() == "true")
```

**Test:** Der Test `test_value_as_string_false_bug` prüft diesen Fall. Aktuell wird er bestanden, weil der Mock-LLM die Capabilities mit `False` und leerem Evidence setzt – die Logik trifft nie `decisions[key] = True`. Ein robusterer Umgang mit String-Werten wäre trotzdem sinnvoll.

---

### 2.4 Kein Fehlerhandling bei ungültigem LLM-JSON

**Ort:** Zeile 170, `_extract_from_chunk`

**Problem:** `json.loads(raw)` kann `json.JSONDecodeError` werfen, wenn das LLM ungültiges JSON liefert. Es gibt kein `try/except`, der Fehler propagiert ungefiltert.

**Empfehlung:** Entweder explizit `JSONDecodeError` fangen und mit nützlicher Fehlermeldung weiterwerfen, oder die Exception durchreichen lassen (klar dokumentieren).

---

### 2.5 Leerer Text / leere Chunks

**Verhalten:** Bei leerem Text liefert `_chunk_text("")` `[""]` (ein leerer Chunk). Der LLM wird mit leerem Prompt aufgerufen. Das funktioniert technisch, ist aber inhaltlich fragwürdig. Ein frühzeitiger Check auf leeren Input könnte sinnvoll sein.

---

## 3. Was funktioniert

- **Modelle** (`FacilityInfo`, `Capabilities`, `Metadata`, `CapabilitySchema`, `EvidenceSnippet`, `CapabilityDecision`) validieren korrekt
- **Chunking** (`_chunk_text`) mit Paragraphen, Overlap und Fallbacks
- **Extraktion** über den LLM-Extractor mit gültigem JSON
- **Aggregation** von Facility-Info und Capabilities über mehrere Chunks
- **Suspicious-Claims-Erkennung** mit Phrasen wie „world-class“, „state-of-the-art“
- **`build_capability_decisions`** mit `CapabilitySchema` und Dict-Input
- **`_normalize_evidence`** für String- und Dict-Evidence
- **`_dedupe_snippets`** und **`_most_common_non_empty`** arbeiten wie erwartet

---

## 4. Test-Suite

**Pfad:** `backend/tests/test_idp.py`, `backend/tests/test_decision.py`  
**Lauf:** `cd backend && $env:PYTHONPATH="." ; python -m pytest tests/ -v`

**Abgedeckte Bereiche:**
- Modelle (FacilityInfo, Capabilities, Metadata, CapabilitySchema, EvidenceSnippet)
- IDPAgent (Parsing, Chunking, JSON-Fehler, value-as-string, suspicious claims, Hilfsfunktionen)
- `build_capability_decisions` (Schema- und Dict-Input, String-Evidence)
- Pydantic-Feldzugriff (v1 vs. v2)

---

## 5. Empfohlene nächste Schritte

1. `parsed.json(indent=2)` durch `parsed.model_dump_json(indent=2)` ersetzen, damit der Demo-Block läuft
2. Migration auf Pydantic v2 APIs (`model_dump`, `model_fields`, `field_validator`, `model_validator`) planen
3. Robusteren Umgang mit LLM-Werten implementieren (z. B. String-`"value"` korrekt interpretieren)
4. `requirements.txt` ergänzen: `pydantic>=2.0`, `typing_extensions`
