import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.detection_service import detect_uploaded_video_keyframes


class VideoDetectionServiceTest(unittest.TestCase):
    def test_video_keyframe_detection_returns_frame_images_and_summary(self):
        upload = type("Upload", (), {"filename": "road.mp4"})()
        upload_path = Path("uploads/road.mp4")
        frame = object()
        cap = Mock()
        cap.isOpened.return_value = True
        cap.get.side_effect = [100, 25]
        cap.read.return_value = (True, frame)

        detection_result = {
            "detections": [
                {
                    "class_name": "person",
                    "confidence": 0.88,
                    "bbox": [10, 20, 100, 220],
                    "risk": {"level": "high", "score": 90},
                }
            ],
            "inference_time_ms": 12.5,
        }

        with (
            patch("backend.services.detection_service.save_upload", return_value=upload_path),
            patch("cv2.VideoCapture", return_value=cap),
            patch("cv2.imwrite", return_value=True),
            patch("backend.services.detection_service.detect_image", return_value=detection_result),
            patch(
                "backend.services.detection_service.render_detection_image",
                side_effect=lambda frame_path, detections: Path("results") / f"{frame_path.stem}_result.jpg",
            ),
            patch("backend.services.detection_service.append_history"),
        ):
            result = detect_uploaded_video_keyframes(upload, confidence=0.5, max_frames=5)

        self.assertEqual(result["frame_count"], 5)
        self.assertEqual(result["count"], 5)
        self.assertEqual(result["max_risk_level"], "high")
        self.assertEqual(result["max_risk_score"], 90)
        self.assertEqual(result["risk_counts"]["high"], 5)
        self.assertEqual(result["inference_time_ms"], 62.5)
        self.assertEqual(result["frames"][0]["result_filename"], "road_frame_1_result.jpg")
        self.assertEqual(result["frames"][0]["result_path"], "results\\road_frame_1_result.jpg")
        self.assertEqual(len(result["video_timeline"]), 5)
        self.assertEqual(result["video_timeline"][0]["trend"], "起始")
        self.assertIn("scene_type", result["scene_summary"])
        self.assertTrue(result["demo_script"])


if __name__ == "__main__":
    unittest.main()
