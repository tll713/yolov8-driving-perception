import unittest

from backend.services.simulation_service import list_simulation_presets, simulate_risk


class SimulationServiceTest(unittest.TestCase):
    def test_list_presets_contains_demo_scenarios(self):
        presets = list_simulation_presets()
        keys = {item["key"] for item in presets}

        self.assertIn("pedestrian_crossing", keys)
        self.assertIn("front_car_brake", keys)

    def test_simulate_risk_returns_timeline_and_peak(self):
        result = simulate_risk({"scenario": "pedestrian_crossing", "duration_sec": 3, "step_sec": 1})

        self.assertEqual(result["scenario"], "pedestrian_crossing")
        self.assertEqual(len(result["timeline"]), 4)
        self.assertIn("score", result["peak_risk"])
        self.assertGreaterEqual(result["peak_risk"]["score"], 0)
        self.assertTrue(result["summary"])

    def test_invalid_speed_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_risk({"ego_speed_kmh": 180})


if __name__ == "__main__":
    unittest.main()
