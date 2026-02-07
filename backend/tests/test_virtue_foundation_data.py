"""
Tests for Virtue Foundation Ghana CSV and Scheme Documentation data.
Runs full pipeline (idp, orchestration, aggregation, models) with real data.
"""
import csv
import json
import re
from pathlib import Path

import pytest

# Setup path
import sys
backend_dir = Path(__file__).resolve().parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pipelines.orchestration import run_pipeline, _demo_llm_extractor
from pipelines.trace import build_pipeline_trace
from features.aggregation.medical_desert_assessor import assess_medical_desert
from features.models.shared import FacilityWithCapabilityDecisions, RegionalAssessment
from features.idp.extraction_agent import IDPAgent
from features.idp.schemas import CapabilitySchema
from features.decision.capability_decision import build_capability_decisions


CSV_PATH = Path(__file__).resolve().parent / "Virtue Foundation Ghana v0.3 - Sheet1.csv"


def _parse_json_array(val):
    """Parse CSV column that may contain JSON array like '["a","b"]'."""
    if not val or str(val).strip() in ("null", "None", ""):
        return []
    s = str(val).strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            out = json.loads(s.replace('""', '"'))
            return out if isinstance(out, list) else []
        except json.JSONDecodeError:
            return []
    return [s] if s else []


def _csv_row_to_document(row: dict) -> str:
    """Build a text document from a CSV row for IDP extraction."""
    parts = []
    if row.get("name"):
        parts.append(f"Facility: {row['name']}")
    if row.get("description"):
        parts.append(f"Description: {row['description']}")
    if row.get("address_city"):
        parts.append(f"City: {row['address_city']}")
    if row.get("address_stateOrRegion"):
        parts.append(f"Region: {row['address_stateOrRegion']}")
    if row.get("address_country"):
        parts.append(f"Country: {row['address_country']}")
    procs = _parse_json_array(row.get("procedure"))
    if procs:
        parts.append("Procedures: " + "; ".join(str(p) for p in procs[:5]))
    eq = _parse_json_array(row.get("equipment"))
    if eq:
        parts.append("Equipment: " + "; ".join(str(e) for e in eq[:5]))
    caps = _parse_json_array(row.get("capability"))
    if caps:
        parts.append("Capabilities: " + "; ".join(str(c) for c in caps[:10]))
    specs = _parse_json_array(row.get("specialties"))
    if specs:
        parts.append("Specialties: " + ", ".join(str(s) for s in specs[:5]))
    return "\n".join(parts) if parts else row.get("name", "Unknown facility")


def _virtue_foundation_llm_extractor(prompt: str) -> str:
    """
    Map Virtue Foundation-style text to idp schema.
    Infers oncology capabilities from procedure, equipment, capability keywords.
    Evidence as strings - pipeline enriches with document_id/chunk_id.
    """
    text = prompt.split("TEXT:\n", 1)[-1] if "TEXT:\n" in prompt else prompt
    text_lower = text.lower()

    def has_kw(*keywords):
        return any(kw in text_lower for kw in keywords)

    def cap_entry(value: bool, conf: float, evidence_list: list):
        return {
            "value": value,
            "confidence": conf,
            "evidence": evidence_list if evidence_list else [],
        }

    caps = {
        "oncology_services": cap_entry(
            has_kw("oncology", "cancer", "chemotherapy", "radiation"),
            0.75 if has_kw("oncology", "cancer", "chemotherapy") else 0.0,
            ["oncology/cancer services mentioned"] if has_kw("oncology", "cancer", "chemotherapy") else [],
        ),
        "ct_scanner": cap_entry(
            has_kw("ct ", "ct scanner", "computed tomography"),
            0.8 if has_kw("ct ", "ct scanner", "computed tomography") else 0.0,
            ["CT scanner mentioned"] if has_kw("ct ", "ct scanner", "computed tomography") else [],
        ),
        "mri_scanner": cap_entry(
            has_kw("mri", "magnetic resonance"),
            0.8 if has_kw("mri", "magnetic resonance") else 0.0,
            ["MRI mentioned"] if has_kw("mri", "magnetic resonance") else [],
        ),
        "pathology_lab": cap_entry(
            has_kw("pathology", "laboratory", "lab ", "diagnostic lab"),
            0.7 if has_kw("pathology", "laboratory", "lab ") else 0.0,
            ["Pathology/lab mentioned"] if has_kw("pathology", "laboratory", "lab ") else [],
        ),
        "genomic_testing": cap_entry(
            has_kw("genomic", "genetic", "sequencing"),
            0.7 if has_kw("genomic", "genetic", "sequencing") else 0.0,
            ["Genomic testing mentioned"] if has_kw("genomic", "genetic", "sequencing") else [],
        ),
        "chemotherapy_delivery": cap_entry(
            has_kw("chemotherapy", "chemo"),
            0.75 if has_kw("chemotherapy", "chemo") else 0.0,
            ["Chemotherapy mentioned"] if has_kw("chemotherapy", "chemo") else [],
        ),
        "radiotherapy": cap_entry(
            has_kw("radiotherapy", "radiation therapy", "radiation treatment"),
            0.75 if has_kw("radiotherapy", "radiation") else 0.0,
            ["Radiotherapy mentioned"] if has_kw("radiotherapy", "radiation") else [],
        ),
        "icu": cap_entry(
            has_kw("icu", "intensive care"),
            0.8 if has_kw("icu", "intensive care") else 0.0,
            ["ICU mentioned"] if has_kw("icu", "intensive care") else [],
        ),
        "trial_coordinator": cap_entry(
            has_kw("trial", "clinical trial", "research"),
            0.6 if has_kw("trial", "clinical trial", "research") else 0.0,
            ["Trial/research mentioned"] if has_kw("trial", "clinical trial", "research") else [],
        ),
    }

    # Extract facility name
    m = re.search(r"Facility:\s*(.+)", text, re.I)
    name = m.group(1).strip() if m else "Unknown Facility"
    m_country = re.search(r"Country:\s*(.+)", text, re.I)
    country = m_country.group(1).strip() if m_country else None
    m_region = re.search(r"Region:\s*(.+)", text, re.I)
    region = m_region.group(1).strip() if m_region else None

    payload = {
        "facility_name": name or "Unknown Facility",
        "country": country,
        "region": region,
        "capabilities": caps,
        "suspicious_claims": [],
    }
    return json.dumps(payload)


def _csv_row_to_pre_extracted_json(row: dict, doc_id: str, chunk_id: str) -> str:
    """
    Convert CSV row to pre-extracted idp JSON with document_id/chunk_id in evidence.
    Maps Virtue Foundation schema to CancerCompass idp schema.
    """
    text_lower = (str(row.get("description", "")) + " " + str(row.get("capability", "")) + " " + str(row.get("equipment", "")) + " " + str(row.get("procedure", ""))).lower()
    doc_id = doc_id
    chunk_id = chunk_id

    def ev(txt):
        return {"text": txt, "document_id": doc_id, "chunk_id": chunk_id}

    def cap(val, conf, ev_list):
        return {"value": val, "confidence": conf, "evidence": [ev(e) for e in ev_list]}

    caps = {
        "oncology_services": cap("oncology" in text_lower or "cancer" in text_lower or "chemotherapy" in text_lower, 0.7 if "oncology" in text_lower or "cancer" in text_lower else 0.0, ["oncology/cancer"] if "oncology" in text_lower or "cancer" in text_lower else []),
        "ct_scanner": cap("ct " in text_lower or "ct scanner" in text_lower, 0.8 if "ct " in text_lower or "ct scanner" in text_lower else 0.0, ["CT scanner"] if "ct " in text_lower or "ct scanner" in text_lower else []),
        "mri_scanner": cap("mri" in text_lower or "magnetic resonance" in text_lower, 0.8 if "mri" in text_lower else 0.0, ["MRI"] if "mri" in text_lower else []),
        "pathology_lab": cap("pathology" in text_lower or "laboratory" in text_lower or " lab " in text_lower, 0.7 if "pathology" in text_lower or "laboratory" in text_lower else 0.0, ["pathology/lab"] if "pathology" in text_lower or "laboratory" in text_lower else []),
        "genomic_testing": cap("genomic" in text_lower or "genetic" in text_lower, 0.7 if "genomic" in text_lower else 0.0, ["genomic"] if "genomic" in text_lower else []),
        "chemotherapy_delivery": cap("chemotherapy" in text_lower or "chemo" in text_lower, 0.75 if "chemotherapy" in text_lower else 0.0, ["chemotherapy"] if "chemotherapy" in text_lower else []),
        "radiotherapy": cap("radiotherapy" in text_lower or "radiation therapy" in text_lower, 0.75 if "radiotherapy" in text_lower else 0.0, ["radiotherapy"] if "radiotherapy" in text_lower else []),
        "icu": cap("icu" in text_lower or "intensive care" in text_lower, 0.8 if "icu" in text_lower or "intensive care" in text_lower else 0.0, ["ICU"] if "icu" in text_lower or "intensive care" in text_lower else []),
        "trial_coordinator": cap("trial" in text_lower or "research" in text_lower, 0.6 if "trial" in text_lower else 0.0, ["trial/research"] if "trial" in text_lower else []),
    }

    bool_caps = {k: v["value"] for k, v in caps.items()}
    conf_caps = {k: v["confidence"] for k, v in caps.items()}
    ev_caps = {k: v["evidence"] for k, v in caps.items()}

    return json.dumps({
        "facility_info": {
            "facility_name": row.get("name", "Unknown") or "Unknown",
            "country": row.get("address_country") or None,
            "region": row.get("address_stateOrRegion") or row.get("address_city") or None,
        },
        "capabilities": bool_caps,
        "metadata": {
            "confidence_scores": conf_caps,
            "extracted_evidence": ev_caps,
            "suspicious_claims": [],
        },
    })


class TestVirtueFoundationData:
    @pytest.fixture
    def csv_rows(self):
        if not CSV_PATH.exists():
            pytest.skip(f"CSV not found: {CSV_PATH}")
        rows = []
        with open(CSV_PATH, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 20:
                    break
                rows.append(row)
        return rows

    def test_csv_loads_and_parses(self, csv_rows):
        assert len(csv_rows) > 0
        row = csv_rows[0]
        assert "name" in row or "source_url" in row

    def test_csv_row_to_document(self, csv_rows):
        doc = _csv_row_to_document(csv_rows[0])
        assert len(doc) > 0
        assert "Facility:" in doc or "Unknown" in doc

    def test_pipeline_with_virtue_foundation_raw_text(self, csv_rows):
        docs = [_csv_row_to_document(r) for r in csv_rows[:5]]
        result = run_pipeline(docs, llm_extractor=_virtue_foundation_llm_extractor)
        assert len(result.raw_idp_output) == 5
        assert len(result.capability_decisions) == 5
        assert len(result.regional_assessments) >= 1

    def test_pipeline_with_pre_extracted_virtue_json(self, csv_rows):
        docs = []
        for i, row in enumerate(csv_rows[:5]):
            docs.append(_csv_row_to_pre_extracted_json(row, f"DOC-{i+1:03d}", f"chunk-{i}"))
        result = run_pipeline(docs, llm_extractor=_virtue_foundation_llm_extractor)
        assert len(result.raw_idp_output) == 5
        assert len(result.capability_decisions) == 5

    def test_trace_with_virtue_data(self, csv_rows):
        docs = [_csv_row_to_document(r) for r in csv_rows[:3]]
        result = run_pipeline(docs, llm_extractor=_virtue_foundation_llm_extractor)
        trace = build_pipeline_trace(result)
        assert len(trace.steps) == 3
        assert trace.steps[1].step_name == "capability_decisions"

    def test_aggregation_with_virtue_style_decisions(self):
        facilities = [
            FacilityWithCapabilityDecisions(
                facility_id="VF-001",
                region="Greater Accra",
                capability_decisions={
                    "oncology_services": {"value": True, "decision_reason": "direct_evidence"},
                    "ct_scanner": {"value": True, "decision_reason": "direct_evidence"},
                    "mri_scanner": {"value": False, "decision_reason": "insufficient_evidence"},
                    "pathology_lab": {"value": True, "decision_reason": "direct_evidence"},
                    "chemotherapy_delivery": {"value": True, "decision_reason": "direct_evidence"},
                    "icu": {"value": True, "decision_reason": "direct_evidence"},
                },
            ),
        ]
        result = assess_medical_desert(facilities)
        assert len(result) == 1
        assert result[0].region == "Greater Accra"
        assert result[0].risk_level.level == "low"
