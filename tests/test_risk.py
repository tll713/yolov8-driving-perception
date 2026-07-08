import unittest

from risk import assess_detection, assess_detections, summarize_risk


class RiskAssessmentTest(unittest.TestCase):
    def test_person_in_lower_center_driving_corridor_is_high_risk(self):
        detection = {
            "class_name": "person",
            "confidence": 0.86,
            "bbox": [420, 360, 560, 700],
        }

        result = assess_detection(detection, image_width=960, image_height=720)

        self.assertEqual(result["level"], "high")
        self.assertGreaterEqual(result["score"], 80)
        self.assertIn("行人", result["message"])
        self.assertIn("行驶路径", result["reason"])

    def test_far_edge_vehicle_is_not_marked_high_risk(self):
        detection = {
            "class_name": "car",
            "confidence": 0.9,
            "bbox": [20, 120, 170, 250],
        }

        result = assess_detection(detection, image_width=1280, image_height=720)

        self.assertIn(result["level"], {"low", "medium"})
        self.assertLess(result["score"], 70)
        self.assertLess(result["lane_overlap"], 0.4)

    def test_side_person_is_medium_not_high_when_outside_driving_corridor(self):
        detection = {
            "class_name": "person",
            "confidence": 0.92,
            "bbox": [20, 410, 150, 710],
        }

        result = assess_detection(detection, image_width=1280, image_height=720)

        self.assertEqual(result["level"], "medium")
        self.assertLess(result["lane_overlap"], 0.4)
        self.assertIn("侧向", result["reason"])

    def test_low_confidence_detection_is_downgraded(self):
        detection = {
            "class_name": "person",
            "confidence": 0.31,
            "bbox": [540, 390, 690, 710],
        }

        result = assess_detection(detection, image_width=1280, image_height=720)

        self.assertEqual(result["level"], "medium")
        self.assertLess(result["confidence_score"], 20)
        self.assertIn("置信度偏低", result["reason"])

    def test_traffic_light_is_information_not_collision_risk(self):
        detection = {
            "class_name": "traffic light",
            "confidence": 0.88,
            "bbox": [610, 70, 660, 180],
        }

        result = assess_detection(detection, image_width=1280, image_height=720)

        self.assertEqual(result["level"], "info")
        self.assertLessEqual(result["score"], 25)
        self.assertIn("交通提示", result["message"])

    def test_assess_detections_adds_realistic_algorithm_fields(self):
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
        self.assertEqual(result[0]["zone"], "middle-left")
        self.assertIn("risk_score", result[0])
        self.assertIn("proximity_score", result[0])
        self.assertIn("distance_score", result[0])
        self.assertIn("lane_overlap", result[0])
        self.assertIn("risk_reason", result[0])

    def test_large_center_vehicle_is_high_risk_with_explainable_reason(self):
        detection = {
            "class_name": "truck",
            "confidence": 0.93,
            "bbox": [260, 260, 740, 760],
        }

        result = assess_detection(detection, image_width=1000, image_height=800)

        self.assertEqual(result["level"], "high")
        self.assertGreaterEqual(result["score"], 80)
        self.assertIn("卡车", result["message"])
        self.assertIn("距离较近", result["reason"])

    def test_summarize_risk_returns_max_level_counts_and_score(self):
        detections = [
            {"risk": {"level": "medium", "score": 55}},
            {"risk": {"level": "high", "score": 88}},
            {"risk": {"level": "info", "score": 20}},
        ]

        summary = summarize_risk(detections)

        self.assertEqual(summary["max_risk_level"], "high")
        self.assertEqual(summary["max_risk_score"], 88)
        self.assertEqual(summary["risk_counts"]["medium"], 1)
        self.assertEqual(summary["risk_counts"]["high"], 1)
        self.assertEqual(summary["risk_counts"]["info"], 1)


if __name__ == "__main__":
    unittest.main()
