import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.detection_service import detect_uploaded_image


class DetectionPersistenceTest(unittest.TestCase):
    def test_detect_uploaded_image_persists_result_and_returns_record_id(self):
        upload = type("Upload", (), {"filename": "road_001.jpg"})()
        upload_path = Path("uploads/road_001.jpg")
        detections = [
            {
                "class_name": "person",
                "confidence": 0.8765,
                "bbox": [520, 360, 650, 700],
                "risk": {"level": "high", "message": "高风险：前方中央区域检测到行人"},
            }
        ]

        with (
            patch("backend.services.detection_service.save_upload", return_value=upload_path),
            patch("backend.services.detection_service.detect_image", return_value=detections),
            patch("backend.services.detection_service.read_image_size", return_value=(1280, 720), create=True),
            patch("backend.services.detection_service.save_detection_result", return_value=101, create=True) as save_result,
            patch("backend.services.detection_service.append_history") as append_history,
        ):
            result = detect_uploaded_image(upload, confidence=0.5)

        self.assertEqual(result.get("record_id"), 101)
        self.assertEqual(result.get("image_width"), 1280)
        self.assertEqual(result.get("image_height"), 720)
        self.assertIn("inference_time_ms", result)
        save_result.assert_called_once()
        append_history.assert_called_once_with(result)


if __name__ == "__main__":
    unittest.main()
