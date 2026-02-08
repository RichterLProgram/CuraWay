import unittest

from src.supply.facility_parser import parse_facility_document


class FacilityParserTests(unittest.TestCase):
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
        self.assertEqual(result.location.region, "Greater Accra")
        self.assertIn("Diagnostic_imaging", result.capabilities)
        self.assertIn("Emergency_care", result.capabilities)
        self.assertIn("X-ray", result.equipment)
        self.assertIn("Surgeons", result.specialists)

    def test_parse_facility_document_missing_fields(self):
        text = (
            "Facility Document\n"
            "Name: Minimal Clinic\n"
            "Location: Tamale, Ghana\n"
        )
        result = parse_facility_document(text)
        self.assertEqual(result.name, "Minimal Clinic")
        self.assertEqual(result.equipment, [])
        self.assertEqual(result.specialists, [])
        self.assertGreaterEqual(result.coverage_score, 0)


if __name__ == "__main__":
    unittest.main()
