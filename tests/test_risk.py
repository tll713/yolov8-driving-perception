import unittest

from risk import assess_detection, assess_detections, summarize_risk


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
        self.assertIn("中央区域", result["message"])

    def test_assess_detections_adds_backend_storage_fields(self):
        detections = [
            {
                "class_name": "car",
                "confidence": 0.91,
                "bbox": [100, 200, 300, 500],
            }
        ]

        result = assess_detections(detections, image_width=1000, image_height=800)

        self.assertEqual(result[0]["class_name_cn"], "汽车")
        self.assertEqual(result[0]["bbox_area"], 60000)
        self.assertEqual(result[0]["center_x"], 200)
        self.assertEqual(result[0]["center_y"], 350)
        self.assertIn("risk_reason", result[0])

    def test_summarize_risk_returns_max_level_and_counts(self):
        detections = [
            {"risk": {"level": "medium"}},
            {"risk": {"level": "high"}},
            {"risk": {"level": "info"}},
        ]

        summary = summarize_risk(detections)

        self.assertEqual(summary["max_risk_level"], "high")
        self.assertEqual(summary["risk_counts"]["medium"], 1)
        self.assertEqual(summary["risk_counts"]["high"], 1)
        self.assertEqual(summary["risk_counts"]["info"], 1)


if __name__ == "__main__":
    unittest.main()
