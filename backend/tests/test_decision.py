"""Tests for decision/capability_decision.py – Deterministische Entscheidung + Why."""
import pytest

import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from features.idp.schemas import FacilityInfo, Capabilities, Metadata, CapabilitySchema
from features.decision.capability_decision import build_capability_decisions


class TestBuildCapabilityDecisions:
    def test_with_capability_schema(self):
        fi = FacilityInfo(facility_name="X")
        cap = Capabilities(
            oncology_services=True, ct_scanner=True, mri_scanner=False,
            pathology_lab=False, genomic_testing=False, chemotherapy_delivery=False,
            radiotherapy=False, icu=False, trial_coordinator=False,
        )
        keys = list(Capabilities.model_fields.keys())
        meta = Metadata(
            confidence_scores={k: 0.7 for k in keys},
            extracted_evidence={k: ["evidence"] if k in ("oncology_services", "ct_scanner") else [] for k in keys},
            suspicious_claims=[],
        )
        schema = CapabilitySchema(facility_info=fi, capabilities=cap, metadata=meta)
        decisions = build_capability_decisions(schema)
        assert "oncology_services" in decisions
        assert decisions["oncology_services"].value is True

    def test_with_dict_input(self):
        keys = [
            "oncology_services", "ct_scanner", "mri_scanner", "pathology_lab",
            "genomic_testing", "chemotherapy_delivery", "radiotherapy", "icu", "trial_coordinator",
        ]
        d = {
            "capabilities": {k: False for k in keys},
            "metadata": {
                "confidence_scores": {k: 0.0 for k in keys},
                "extracted_evidence": {k: [] for k in keys},
                "suspicious_claims": [],
            },
        }
        decisions = build_capability_decisions(d)
        assert len(decisions) == 9

    def test_string_evidence_normalized(self):
        """Evidence can be plain strings; _normalize_evidence handles them."""
        fi = FacilityInfo(facility_name="X")
        cap = Capabilities(
            oncology_services=True, ct_scanner=False, mri_scanner=False,
            pathology_lab=False, genomic_testing=False, chemotherapy_delivery=False,
            radiotherapy=False, icu=False, trial_coordinator=False,
        )
        keys = list(Capabilities.model_fields.keys())
        meta = Metadata(
            confidence_scores={k: 0.8 for k in keys},
            extracted_evidence={
                "oncology_services": ["We have oncology"],
                **{k: [] for k in keys if k != "oncology_services"},
            },
            suspicious_claims=[],
        )
        schema = CapabilitySchema(facility_info=fi, capabilities=cap, metadata=meta)
        decisions = build_capability_decisions(schema)
        ev = decisions["oncology_services"].evidence
        assert len(ev) == 1
        assert ev[0].text == "We have oncology"
        assert ev[0].document_id == "unknown"
