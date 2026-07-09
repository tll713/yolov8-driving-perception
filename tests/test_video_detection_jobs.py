import importlib.util
import unittest
from io import BytesIO
from unittest.mock import patch


@unittest.skipIf(importlib.util.find_spec("flask") is None, "Flask is not installed in this runtime")
class VideoDetectionJobRouteTest(unittest.TestCase):
    def setUp(self):
        from backend.app import create_app

        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def test_create_video_detection_job_returns_job_id_immediately(self):
        with patch("backend.routes.detections.start_video_detection_job", return_value={"job_id": "job-1", "status": "queued"}):
            response = self.client.post(
                "/api/detections/videos/jobs",
                data={"file": (BytesIO(b"fake video"), "road.mp4"), "confidence": "0.5"},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 202)
        payload = response.get_json()
        self.assertEqual(payload["code"], 0)
        self.assertEqual(payload["data"]["job_id"], "job-1")
        self.assertEqual(payload["data"]["status"], "queued")

    def test_get_video_detection_job_status_returns_latest_frame(self):
        job = {
            "job_id": "job-1",
            "status": "running",
            "progress": 40,
            "latest_frame": {
                "frame_index": 12,
                "timestamp_sec": 1.2,
                "image_url": "/results/job-1_frame_12.jpg",
                "detections": [{"class_name": "car"}],
            },
            "detection_timeline": [
                {
                    "frame_index": 12,
                    "timestamp_sec": 1.2,
                    "image_width": 1280,
                    "image_height": 720,
                    "detections": [{"class_name": "car"}],
                }
            ],
        }

        with patch("backend.routes.detections.get_video_detection_job", return_value=job):
            response = self.client.get("/api/detections/videos/jobs/job-1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["data"]["status"], "running")
        self.assertEqual(payload["data"]["latest_frame"]["frame_index"], 12)
        self.assertEqual(payload["data"]["detection_timeline"][0]["timestamp_sec"], 1.2)

    def test_get_missing_video_detection_job_returns_404(self):
        with patch("backend.routes.detections.get_video_detection_job", return_value=None):
            response = self.client.get("/api/detections/videos/jobs/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
