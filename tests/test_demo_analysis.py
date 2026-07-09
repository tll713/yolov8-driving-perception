import unittest

from backend.services.demo_analysis_service import (
    build_dashboard,
    build_decision_trace,
    build_safety_advice,
    build_scene_summary,
)


class DemoAnalysisServiceTest(unittest.TestCase):
    def test_build_safety_advice_prioritizes_high_risk_person(self):
        detections = [
            {
                "class_name": "person",
                "class_name_cn": "person",
                "risk": {"level": "high", "score": 91},
            }
        ]

        advice = build_safety_advice(detections)

        self.assertEqual(advice[0]["level"], "high")
        self.assertIn("person", advice[0]["message"])

    def test_build_dashboard_summarizes_history_items(self):
        items = [
            {
                "count": 3,
                "max_risk_level": "high",
                "inference_time_ms": 120,
                "detections": [{"class_name_cn": "car"}, {"class_name_cn": "person"}],
            },
            {
                "count": 1,
                "max_risk_level": "low",
                "inference_time_ms": 80,
                "detections": [{"class_name_cn": "car"}],
            },
        ]

        dashboard = build_dashboard(items)

        self.assertEqual(dashboard["total_records"], 2)
        self.assertEqual(dashboard["total_objects"], 4)
        self.assertEqual(dashboard["high_risk_records"], 1)
        self.assertEqual(dashboard["average_inference_time_ms"], 100)
        self.assertEqual(dashboard["top_classes"][0]["class_name"], "car")

    def test_scene_summary_identifies_primary_risk_target(self):
        detections = [
            {
                "class_name": "person",
                "class_name_cn": "person",
                "lane_overlap": 0.8,
                "distance_score": 75,
                "risk": {"level": "high", "score": 88},
            },
            {
                "class_name": "car",
                "class_name_cn": "car",
                "lane_overlap": 0.1,
                "distance_score": 40,
                "risk": {"level": "low", "score": 28},
            },
        ]

        summary = build_scene_summary(detections)

        self.assertEqual(summary["lane_target_count"], 1)
        self.assertEqual(summary["close_target_count"], 1)
        self.assertEqual(summary["primary_target"]["class_name"], "person")

    def test_decision_trace_exposes_demo_steps(self):
        detections = [
            {
                "class_name": "truck",
                "class_name_cn": "truck",
                "lane_overlap": 0.55,
                "distance_score": 65,
                "risk": {"level": "medium", "score": 64},
            }
        ]

        trace = build_decision_trace(detections)

        self.assertGreaterEqual(len(trace), 4)
        self.assertTrue(any(item.get("result", "").find("truck") >= 0 for item in trace))


if __name__ == "__main__":
    unittest.main()
