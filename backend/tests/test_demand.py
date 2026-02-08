import os
import unittest

from src.demand.profile_extractor import extract_demand_from_text


class DemandExtractorTests(unittest.TestCase):
    def setUp(self):
        self._prev_llm_disabled = os.getenv("LLM_DISABLED")
        os.environ["LLM_DISABLED"] = "true"

    def tearDown(self):
        if self._prev_llm_disabled is None:
            os.environ.pop("LLM_DISABLED", None)
        else:
            os.environ["LLM_DISABLED"] = self._prev_llm_disabled

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
        self.assertIsInstance(result.profile.patient_id, str)
        self.assertIsInstance(result.profile.diagnosis, str)
        self.assertTrue(result.profile.diagnosis)
        self.assertTrue(result.profile.stage is None or isinstance(result.profile.stage, str))
        self.assertGreaterEqual(result.profile.urgency_score, 0)
        self.assertLessEqual(result.profile.urgency_score, 10)
        self.assertIn(result.travel_radius_km, {30, 60})
        self.assertGreaterEqual(len(result.required_capabilities), 1)

    def test_extract_with_missing_fields(self):
        text = (
            "Patient Report\n"
            "Patient ID: P-200\n"
            "Location: Kumasi, Ashanti, Ghana\n"
            "Diagnosis: Breast cancer\n"
        )
        result = extract_demand_from_text(text)
        self.assertIsInstance(result.profile.patient_id, str)
        self.assertTrue(result.profile.stage is None or isinstance(result.profile.stage, str))
        self.assertIsInstance(result.profile.biomarkers, list)
        self.assertGreaterEqual(result.profile.urgency_score, 0)
        self.assertLessEqual(result.profile.urgency_score, 10)
        self.assertIn(result.travel_radius_km, {30, 60})
        self.assertGreaterEqual(len(result.required_capabilities), 1)


if __name__ == "__main__":
    unittest.main()
