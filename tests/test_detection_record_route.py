import unittest
import importlib.util
from unittest.mock import patch


@unittest.skipIf(importlib.util.find_spec("flask") is None, "Flask is not installed in this runtime")
class DetectionRecordRouteTest(unittest.TestCase):
    def test_get_detection_record_returns_database_record(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True
        record = {
            "record_id": 101,
            "filename": "road_001.jpg",
            "detections": [],
        }

        with patch("backend.routes.detections.get_detection_result", return_value=record):
            response = app.test_client().get("/api/detections/records/101")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], record)


if __name__ == "__main__":
    unittest.main()
