from __future__ import annotations

from typing import List

from src.shared.models import MedicalDesert, PlannerRecommendation


CAPABILITY_ACTIONS = {
    "Emergency_care": "Stand up 24/7 emergency unit with triage protocols.",
    "Surgical_services": "Invest in surgical theatre and perioperative staffing.",
    "Dialysis": "Deploy dialysis center with trained renal nurses.",
    "Diagnostic_imaging": "Add imaging suite with X-ray and ultrasound.",
    "Laboratory_services": "Establish laboratory with basic hematology and chemistry.",
    "Pharmacy": "Set up on-site pharmacy with essential medicines list.",
    "Maternal_care": "Launch maternal unit with antenatal and delivery services.",
    "Oncology": "Create oncology clinic with chemo infusion chairs.",
    "Ophthalmology": "Add eye clinic and referral pathway for surgery.",
}


def generate_recommendations(deserts: List[MedicalDesert]) -> List[PlannerRecommendation]:
    """
    Generate prioritized recommendations for medical deserts.
    """
    recommendations: List[PlannerRecommendation] = []
    for desert in deserts:
        priority = "high" if desert.gap_score >= 0.7 else "medium" if desert.gap_score >= 0.4 else "low"
        actions = [
            CAPABILITY_ACTIONS.get(cap, f"Add capability: {cap}.")
            for cap in desert.missing_capabilities[:4]
        ]
        estimated_cost = 250000 + 50000 * len(actions)
        expected_impact = (
            "Reduce travel time and improve time-to-treatment for high-urgency patients."
        )
        recommendations.append(
            PlannerRecommendation(
                region_name=desert.region_name,
                priority=priority,
                missing_capabilities=desert.missing_capabilities,
                recommended_actions=actions,
                estimated_cost_usd=estimated_cost,
                expected_impact=expected_impact,
            )
        )
    return recommendations
