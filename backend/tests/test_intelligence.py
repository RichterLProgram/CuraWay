import unittest

from src.intelligence.gap_detector import detect_deserts
from src.shared.models import DemandRequirements, FacilityCapabilities, FacilityLocation, PatientProfile


class IntelligenceTests(unittest.TestCase):
    def test_detect_deserts_with_demand_only(self):
        demand = DemandRequirements(
            profile=PatientProfile(
                patient_id="P-1",
                diagnosis="Breast cancer",
                stage="II",
                biomarkers=["HER2 positive"],
                location="Accra, Ghana",
                urgency_score=4,
            ),
            required_capabilities=["Oncology"],
            travel_radius_km=60,
            evidence=["Breast cancer"],
        )
        deserts = detect_deserts([demand], [])
        self.assertEqual(len(deserts), 1)
        self.assertEqual(deserts[0].region_name, "Greater Accra")
        self.assertIn("Oncology", deserts[0].missing_capabilities)
        self.assertGreater(deserts[0].gap_score, 0)

    def test_detect_deserts_with_supply(self):
        demand = DemandRequirements(
            profile=PatientProfile(
                patient_id="P-2",
                diagnosis="Cervical cancer",
                stage="III",
                biomarkers=["HPV positive"],
                location="Tamale, Ghana",
                urgency_score=8,
            ),
            required_capabilities=["Oncology"],
            travel_radius_km=30,
            evidence=["Cervical cancer"],
        )
        facility = FacilityCapabilities(
            facility_id="F-1",
            name="Tamale General Hospital",
            location=FacilityLocation(lat=9.4, lng=-0.83, region="Northern"),
            capabilities=["Oncology"],
            equipment=[],
            specialists=[],
            coverage_score=20,
        )
        deserts = detect_deserts([demand], [facility])
        self.assertEqual(len(deserts), 1)
        self.assertEqual(deserts[0].missing_capabilities, [])


if __name__ == "__main__":
    unittest.main()
