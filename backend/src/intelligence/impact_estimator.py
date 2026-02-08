from __future__ import annotations

from typing import List

from src.shared.models import ImpactEstimate, MedicalDesert


def estimate_impact(deserts: List[MedicalDesert]) -> List[ImpactEstimate]:
    """
    Estimate ROI and time-to-treatment improvements for each desert.
    """
    estimates: List[ImpactEstimate] = []
    for desert in deserts:
        roi_score = min(1.0, 0.3 + desert.gap_score * 0.7)
        time_to_treatment_days = int(21 + (1 - desert.gap_score) * 14)
        estimates.append(
            ImpactEstimate(
                region_name=desert.region_name,
                roi_score=roi_score,
                time_to_treatment_days=time_to_treatment_days,
            )
        )
    return estimates
