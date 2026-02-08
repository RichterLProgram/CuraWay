import unittest

from src.demand.profile_extractor import extract_demand_from_text


class DemandExtractorTests(unittest.TestCase):
    def test_extract_basic_profile(self):
        text = (
            "Patient Report\n"
            "Patient ID: P-100\n"
            "Location: Accra, Greater Accra, Ghana\n"
            "Diagnosis: Non-small cell lung cancer (NSCLC)\n"
            "Stage: IV\n"
            "Biomarkers: EGFR positive, KRAS negative\n"
            "Comorbidities: Hypertension\n"
        )
        result = extract_demand_from_text(text)
        self.assertEqual(result.profile.patient_id, "P-100")
        self.assertIn("NSCLC", result.profile.diagnosis)
        self.assertEqual(result.profile.stage, "IV")
        self.assertIn("EGFR positive", result.profile.biomarkers)
        self.assertEqual(result.profile.urgency_score, 10)
        self.assertEqual(result.travel_radius_km, 30)
        self.assertIn("Oncology", result.required_capabilities)
        self.assertIn("EGFR_targeted_therapy", result.required_capabilities)
        self.assertIn("Chemotherapy", result.required_capabilities)

    def test_extract_with_missing_fields(self):
        text = (
            "Patient Report\n"
            "Patient ID: P-200\n"
            "Location: Kumasi, Ashanti, Ghana\n"
            "Diagnosis: Breast cancer\n"
        )
        result = extract_demand_from_text(text)
        self.assertEqual(result.profile.patient_id, "P-200")
        self.assertEqual(result.profile.stage, None)
        self.assertEqual(result.profile.biomarkers, [])
        self.assertEqual(result.profile.urgency_score, 0)
        self.assertEqual(result.travel_radius_km, 60)
        self.assertIn("Surgical_oncology", result.required_capabilities)
        self.assertIn("Diagnostic_imaging", result.required_capabilities)


if __name__ == "__main__":
    unittest.main()
