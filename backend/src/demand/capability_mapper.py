from __future__ import annotations

from typing import List


def map_demand_to_capabilities(
    diagnosis: str, stage: str | None, biomarkers: List[str]
) -> List[str]:
    diagnosis_lower = diagnosis.lower()
    biomarkers_lower = [b.lower() for b in biomarkers]
    capabilities: List[str] = ["Oncology"]

    if "lung" in diagnosis_lower or "nsclc" in diagnosis_lower:
        capabilities.append("Pulmonology")
        if "egfr" in " ".join(biomarkers_lower):
            capabilities.append("EGFR_targeted_therapy")
        if stage and "iv" in stage.lower():
            capabilities.append("Chemotherapy")

    if "breast" in diagnosis_lower:
        capabilities.extend(["Surgical_oncology", "Diagnostic_imaging"])
        if stage and stage.strip().lower() in {"iii", "iv"}:
            capabilities.append("Radiation_therapy")

    if "cervical" in diagnosis_lower:
        capabilities.extend(["Gynecologic_oncology", "Radiation_therapy"])

    if "prostate" in diagnosis_lower:
        capabilities.extend(["Urology", "Radiation_therapy"])

    return sorted(set(capabilities))
