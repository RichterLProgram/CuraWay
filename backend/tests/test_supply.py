import os
import unittest

from src.supply.facility_parser import parse_facility_document


class FacilityParserTests(unittest.TestCase):
    def setUp(self):
        self._prev_llm_disabled = os.getenv("LLM_DISABLED")
        os.environ["LLM_DISABLED"] = "true"

    def tearDown(self):
        if self._prev_llm_disabled is None:
            os.environ.pop("LLM_DISABLED", None)
        else:
            os.environ["LLM_DISABLED"] = self._prev_llm_disabled

    def test_parse_facility_document(self):
        text = (
            "Facility Document\n"
            "Name: Example Hospital\n"
            "Location: 10 Main St., Accra, Ghana\n"
            "Services: Emergency care, surgeries\n"
            "Equipment: X-ray, CT scanner\n"
            "Specialists: Surgeons, Radiologists\n"
            "Capabilities: Inpatient care, Diagnostic imaging\n"
        )
        result = parse_facility_document(text)
        self.assertEqual(result.name, "Example Hospital")
        self.assertIsInstance(result.location.region, str)
        self.assertGreaterEqual(len(result.capabilities), 1)
        self.assertGreaterEqual(len(result.equipment), 1)
        self.assertGreaterEqual(len(result.specialists), 1)

    def test_parse_facility_document_missing_fields(self):
        text = (
            "Facility Document\n"
            "Name: Minimal Clinic\n"
            "Location: Tamale, Ghana\n"
        )
        result = parse_facility_document(text)
        self.assertIsInstance(result.name, str)
        self.assertIsInstance(result.equipment, list)
        self.assertIsInstance(result.specialists, list)
        self.assertGreaterEqual(result.coverage_score, 0)


if __name__ == "__main__":
    unittest.main()
