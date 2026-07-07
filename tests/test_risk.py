import unittest


from risk import assess_detection


class RiskAssessmentTest(unittest.TestCase):
    def test_person_in_lower_center_is_high_risk(self):
        detection = {
            "class_name": "person",
            "confidence": 0.86,
            "bbox": [420, 360, 560, 700],
        }

        result = assess_detection(detection, image_width=960, image_height=720)

        self.assertEqual(result["level"], "high")
        self.assertIn("行人", result["message"])


if __name__ == "__main__":
    unittest.main()
