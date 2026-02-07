# Virtue Foundation Status (English Summary)

## What this covers
- Facility capability extraction
- Suspicious claim detection
- Medical desert aggregation

## Current status
- IDP output is normalized and auditable
- Capability decisions are conservative by design
- Regional risk scoring is deterministic

## Next steps (optional)
- Add facility-level geocoding for maps
- Improve capability coverage and weighting
# Statusbericht: Virtue Foundation Daten-Integration

**Datum:** 7. Februar 2025  
**Getestet:** Vollständige Pipeline (idp, orchestration, aggregation, models) mit Virtue Foundation Ghana CSV, Scheme Documentation und prompts_and_pydantic_models

---

## Kurzfassung

- **58 Tests** insgesamt – alle bestanden.
- **Virtue Foundation Ghana v0.3 CSV** – erfolgreich in die Pipeline integriert.
- **prompts_and_pydantic_models** – Import-Fehler in `medical_specialties.py` behoben.
- **Keine weiteren Fehler** festgestellt.

---

## 1. Getestete Datenquellen

### Virtue Foundation Ghana v0.3 - Sheet1.csv

- **Größe:** ~1000+ Zeilen (Ghana Healthcare Facilities)
- **Spalten:** name, specialties, procedure, equipment, capability, organization_type, address_*, description, etc.
- **Schema:** Virtue Foundation Scheme Documentation

### Virtue Foundation Scheme Documentation.txt

- Organization Extraction (ngos, facilities, other_organizations)
- Base Organization Fields (Kontakt, Adresse, Web)
- Facility-Specific (facilityTypeId, operatorTypeId, description, etc.)
- Medical Specialties
- Facility Facts (procedure, equipment, capability)

### prompts_and_pydantic_models/

| Modul | Status | Anmerkung |
|-------|--------|-----------|
| organization_extraction.py | OK | OrganizationExtractionOutput |
| facility_and_ngo_fields.py | OK | Facility, NGO, BaseOrganization |
| free_form.py | OK | FacilityFacts (procedure, equipment, capability) |
| medical_specialties.py | Fix angewendet | Import von fdr.config fehlte → Fallback eingebaut |

---

## 2. Behobene Fehler

### medical_specialties.py – fehlende Abhängigkeit fdr.config

**Problem:** `from fdr.config.medical_specialties import MEDICAL_HIERATCHY, flatten_specialties_to_level` – Modul `fdr` nicht vorhanden in CancerCompass.

**Lösung:** Fallback eingebaut – wenn `fdr.config` fehlt, wird eine lokale Spezialitätenliste verwendet:

```python
try:
    from fdr.config.medical_specialties import ...
except ImportError:
    _SPECIALTIES = ["internalMedicine", "familyMedicine", ...]
    MEDICAL_HIERATCHY = {"children": [{"name": s} for s in _SPECIALTIES]}
    def flatten_specialties_to_level(hierarchy, level): return _SPECIALTIES
```

---

## 3. Schema-Mapping: Virtue Foundation → CancerCompass

CancerCompass verwendet ein schlankes Schema für Krebsversorgung:

| CancerCompass | Virtue Foundation (Quelle) |
|---------------|----------------------------|
| facility_name | name |
| country | address_country |
| region | address_stateOrRegion / address_city |
| oncology_services | procedure/equipment/capability mit "oncology", "cancer", "chemotherapy" |
| ct_scanner | equipment/capability mit "CT", "CT scanner" |
| mri_scanner | equipment/capability mit "MRI" |
| pathology_lab | procedure/equipment mit "pathology", "laboratory" |
| genomic_testing | capability mit "genomic", "genetic" |
| chemotherapy_delivery | procedure mit "chemotherapy" |
| radiotherapy | procedure mit "radiotherapy" |
| icu | capability mit "ICU", "intensive care" |
| trial_coordinator | capability mit "trial", "research" |

---

## 4. Neue Test-Suite: test_virtue_foundation_data.py

| Test | Beschreibung |
|------|--------------|
| test_csv_loads_and_parses | CSV wird geladen und geparst |
| test_csv_row_to_document | CSV-Zeile wird in Textdokument konvertiert |
| test_pipeline_with_virtue_foundation_raw_text | Pipeline mit 5 CSV-Zeilen als Raw-Text |
| test_pipeline_with_pre_extracted_virtue_json | Pipeline mit Pre-extracted JSON aus CSV |
| test_trace_with_virtue_data | Trace-Bau mit Virtue-Daten |
| test_aggregation_with_virtue_style_decisions | Aggregation mit Virtue-ähnlichen Decisions |

---

## 5. Test-Ausführung

```powershell
cd backend
$env:PYTHONPATH = "."
python -m pytest test/ -v
```

**Ergebnis:** 58 passed

---

## 6. Empfehlungen

1. **PYTHONPATH:** Für `prompts_and_pydantic_models` beim Import von `medical_specialties` `test/` auf den PYTHONPATH setzen: `$env:PYTHONPATH = ".;test"`.
2. **CSV-Größe:** CSV ist sehr groß (~864k Zeichen); Tests nutzen nur die ersten 5–20 Zeilen.
3. **Schema-Alignment:** Für produktive Nutzung: ggf. gemeinsames Schema oder Mapping zwischen Virtue Foundation und CancerCompass definieren.
