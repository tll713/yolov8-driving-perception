import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.detection_service import detect_uploaded_image


class FakeUpload:
    filename = "road.jpg"

    def save(self, target):
        Path(target).write_bytes(b"fake image bytes")


class DetectionServiceTest(unittest.TestCase):
    def test_detect_uploaded_image_returns_backend_record_fields(self):
        fake_detection_result = {
            "image_width": 1280,
            "image_height": 720,
            "inference_time_ms": 85.2,
            "detections": [
                {
                    "class_name": "person",
                    "class_name_cn": "行人",
                    "confidence": 0.8765,
                    "bbox": [520, 360, 650, 700],
                    "bbox_area": 44200,
                    "center_x": 585,
                    "center_y": 530,
                    "area_ratio": 0.04796,
                    "risk": {
                        "level": "high",
                        "message": "高风险：前方中央区域检测到行人",
                        "reason": "检测到 person，且目标中心位于画面下半部分的中央区域",
                    },
                    "risk_level": "high",
                    "risk_message": "高风险：前方中央区域检测到行人",
                    "risk_reason": "检测到 person，且目标中心位于画面下半部分的中央区域",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result_path = temp_path / "road_result.jpg"

            with patch(
                "backend.services.detection_service.UPLOAD_DIR",
                temp_path,
            ), patch(
                "backend.services.detection_service.detect_image",
                return_value=fake_detection_result,
            ), patch(
                "backend.services.detection_service.render_detection_image",
                return_value=result_path,
            ), patch(
                "backend.services.detection_service.append_history",
            ) as append_history:
                result = detect_uploaded_image(FakeUpload(), confidence=0.6)

        self.assertEqual(result["type"], "image")
        self.assertEqual(result["original_filename"], "road.jpg")
        self.assertEqual(result["confidence_threshold"], 0.6)
        self.assertEqual(result["image_width"], 1280)
        self.assertEqual(result["image_height"], 720)
        self.assertEqual(result["total_objects"], 1)
        self.assertEqual(result["max_risk_level"], "high")
        self.assertEqual(result["risk_counts"]["high"], 1)
        self.assertEqual(result["result_filename"], "road_result.jpg")
        self.assertEqual(result["detections"][0]["risk_level"], "high")
        self.assertIn("scene_type", result["scene_summary"])
        self.assertGreaterEqual(len(result["decision_trace"]), 4)
        self.assertTrue(result["demo_script"])
        self.assertTrue(result["safety_advice"])
        append_history.assert_called_once()


if __name__ == "__main__":
    unittest.main()
