import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.detection_service import detect_uploaded_image


class DetectionPersistenceTest(unittest.TestCase):
    def test_detect_uploaded_image_persists_result_and_returns_record_id(self):
        upload = type("Upload", (), {"filename": "road_001.jpg"})()
        upload_path = Path("uploads/road_001.jpg")
        result_path = Path("results/road_001_result.jpg")
        detections = [
            {
                "class_name": "person",
                "confidence": 0.8765,
                "bbox": [520, 360, 650, 700],
                "risk": {
                    "level": "high",
                    "score": 92,
                    "message": "高风险：前方中央近距离区域检测到行人",
                },
            }
        ]
        detection_result = {
            "image_width": 1280,
            "image_height": 720,
            "inference_time_ms": 31.5,
            "detections": detections,
        }

        with (
            patch("backend.services.detection_service.save_upload", return_value=upload_path),
            patch("backend.services.detection_service.detect_image", return_value=detection_result),
            patch("backend.services.detection_service.render_detection_image", return_value=result_path),
            patch("backend.services.detection_service.save_detection_result", return_value=101) as save_result,
            patch("backend.services.detection_service.append_history") as append_history,
        ):
            result = detect_uploaded_image(upload, confidence=0.5)

        self.assertEqual(result.get("record_id"), 101)
        self.assertEqual(result.get("image_width"), 1280)
        self.assertEqual(result.get("image_height"), 720)
        self.assertEqual(result.get("result_filename"), "road_001_result.jpg")
        self.assertEqual(result.get("max_risk_score"), 92)
        save_result.assert_called_once()
        append_history.assert_called_once_with(result)


if __name__ == "__main__":
    unittest.main()
