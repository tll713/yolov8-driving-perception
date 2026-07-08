import unittest

from backend.services.demo_analysis_service import (
    build_dashboard,
    build_decision_trace,
    build_safety_advice,
    build_scene_summary,
    build_video_timeline,
)


class DemoAnalysisServiceTest(unittest.TestCase):
    def test_build_safety_advice_prioritizes_high_risk_person(self):
        detections = [
            {
                "class_name": "person",
                "class_name_cn": "行人",
                "risk": {"level": "high", "score": 91},
            }
        ]

        advice = build_safety_advice(detections)

        self.assertEqual(advice[0]["level"], "high")
        self.assertIn("减速", advice[0]["message"])
        self.assertIn("行人", advice[0]["message"])

    def test_build_dashboard_summarizes_history_items(self):
        items = [
            {
                "count": 3,
                "max_risk_level": "high",
                "inference_time_ms": 120,
                "detections": [{"class_name_cn": "汽车"}, {"class_name_cn": "行人"}],
            },
            {
                "count": 1,
                "max_risk_level": "low",
                "inference_time_ms": 80,
                "detections": [{"class_name_cn": "汽车"}],
            },
        ]

        dashboard = build_dashboard(items)

        self.assertEqual(dashboard["total_records"], 2)
        self.assertEqual(dashboard["total_objects"], 4)
        self.assertEqual(dashboard["high_risk_records"], 1)
        self.assertEqual(dashboard["average_inference_time_ms"], 100)
        self.assertEqual(dashboard["top_classes"][0]["class_name"], "汽车")

    def test_scene_summary_identifies_primary_risk_target(self):
        detections = [
            {
                "class_name": "person",
                "class_name_cn": "行人",
                "lane_overlap": 0.8,
                "distance_score": 75,
                "risk": {"level": "high", "score": 88},
            },
            {
                "class_name": "car",
                "class_name_cn": "汽车",
                "lane_overlap": 0.1,
                "distance_score": 40,
                "risk": {"level": "low", "score": 28},
            },
        ]

        summary = build_scene_summary(detections)

        self.assertEqual(summary["scene_type"], "前方高风险通行场景")
        self.assertEqual(summary["lane_target_count"], 1)
        self.assertEqual(summary["close_target_count"], 1)
        self.assertEqual(summary["primary_target"]["class_name"], "行人")

    def test_decision_trace_exposes_demo_steps(self):
        detections = [
            {
                "class_name": "truck",
                "class_name_cn": "卡车",
                "lane_overlap": 0.55,
                "distance_score": 65,
                "risk": {"level": "medium", "score": 64},
            }
        ]

        trace = build_decision_trace(detections)

        self.assertGreaterEqual(len(trace), 4)
        self.assertEqual(trace[0]["step"], "目标检测")
        self.assertTrue(any(item["step"] == "主风险目标" for item in trace))

    def test_video_timeline_marks_risk_trend(self):
        timeline = build_video_timeline(
            [
                {"frame_index": 1, "max_risk_level": "low", "max_risk_score": 20, "count": 1},
                {"frame_index": 2, "max_risk_level": "high", "max_risk_score": 70, "count": 2},
                {"frame_index": 3, "max_risk_level": "medium", "max_risk_score": 55, "count": 1},
            ]
        )

        self.assertEqual(timeline[0]["trend"], "起始")
        self.assertEqual(timeline[1]["trend"], "风险上升")
        self.assertEqual(timeline[2]["trend"], "风险下降")


if __name__ == "__main__":
    unittest.main()
