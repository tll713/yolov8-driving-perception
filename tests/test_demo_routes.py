import importlib.util
from io import BytesIO
import unittest
from unittest.mock import patch


@unittest.skipIf(importlib.util.find_spec("flask") is None, "Flask is not installed in this runtime")
class DemoRoutesTest(unittest.TestCase):
    def test_clear_history_endpoint_returns_success(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True

        with patch("backend.routes.detections.clear_history", return_value=None) as clear_history:
            response = app.test_client().post("/api/detections/history/clear")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["code"], 0)
        clear_history.assert_called_once()

    def test_video_detection_returns_key_frame_summary(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True

        with patch(
            "backend.routes.detections.detect_uploaded_video",
            return_value={"type": "video", "detections": [], "count": 0},
        ):
            response = app.test_client().post(
                "/api/detections/videos",
                data={"file": (BytesIO(b"demo"), "road.mp4")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["type"], "video")

    def test_model_info_exposes_runtime_settings(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True
        response = app.test_client().get("/api/models/current")
        data = response.get_json()["data"]

        self.assertIn("inference_mode", data)
        self.assertIn("image_size", data)
        self.assertIn("refine_image_size", data)
        self.assertIn("device", data)

    def test_simulation_presets_endpoint_returns_items(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True
        response = app.test_client().get("/api/simulation/presets")
        data = response.get_json()["data"]

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["items"])

    def test_simulation_risk_endpoint_returns_timeline(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True
        response = app.test_client().post(
            "/api/simulation/risk",
            json={"scenario": "front_car_brake", "duration_sec": 2, "step_sec": 1},
        )
        data = response.get_json()["data"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["scenario"], "front_car_brake")
        self.assertEqual(len(data["timeline"]), 3)
        self.assertIn("peak_risk", data)

    def test_custom_simulation_scenario_endpoints(self):
        from backend.app import create_app

        app = create_app()
        app.testing = True
        scenario = {"id": "custom-1", "name": "测试场景"}
        with patch("backend.routes.simulation.list_custom_scenarios", return_value=[scenario]):
            response = app.test_client().get("/api/simulation/scenarios")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["items"], [scenario])

        with patch("backend.routes.simulation.save_custom_scenario", return_value=scenario):
            response = app.test_client().post("/api/simulation/scenarios", json={"name": "测试场景"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], scenario)


if __name__ == "__main__":
    unittest.main()
