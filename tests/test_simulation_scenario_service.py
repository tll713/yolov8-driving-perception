import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.simulation_scenario_service import (
    delete_custom_scenario,
    list_custom_scenarios,
    save_custom_scenario,
)


class SimulationScenarioServiceTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory(dir="logs")
        self.scenario_file = Path(self.temporary_directory.name) / "simulation_scenarios.json"
        self.file_patch = patch(
            "backend.services.simulation_scenario_service.SIMULATION_SCENARIO_FILE",
            self.scenario_file,
        )
        self.file_patch.start()

    def tearDown(self):
        self.file_patch.stop()
        self.temporary_directory.cleanup()

    def test_save_update_list_and_delete_custom_scenario(self):
        saved = save_custom_scenario(
            {
                "name": "自定义横穿场景",
                "description": "用于验证场景持久化",
                "weather": "rain",
                "ego_speed_kmh": 35,
                "duration_sec": 3,
                "aeb_safety_margin_m": 3,
                "targets": [
                    {
                        "id": "person",
                        "class_name": "person",
                        "distance_m": 25,
                        "lateral_m": -3,
                    }
                ],
                "events": [
                    {"time_sec": 1, "target_id": "person", "lateral_speed_mps": 1.2}
                ],
            }
        )

        self.assertTrue(saved["key"].startswith("custom:"))
        self.assertEqual(saved["aeb_safety_margin_m"], 3)
        self.assertEqual(list_custom_scenarios()[0]["name"], "自定义横穿场景")

        updated = save_custom_scenario({**saved, "name": "更新后的场景"})
        self.assertEqual(updated["name"], "更新后的场景")
        self.assertEqual(len(list_custom_scenarios()), 1)

        self.assertTrue(delete_custom_scenario(saved["id"]))
        self.assertEqual(list_custom_scenarios(), [])

    def test_invalid_event_target_is_rejected_before_persistence(self):
        with self.assertRaisesRegex(ValueError, "不存在的目标"):
            save_custom_scenario(
                {
                    "name": "无效场景",
                    "targets": [{"id": "car", "class_name": "car", "distance_m": 20}],
                    "events": [
                        {"time_sec": 1, "target_id": "missing", "longitudinal_speed_mps": 0}
                    ],
                }
            )

        self.assertFalse(self.scenario_file.exists())

    def test_empty_target_list_is_rejected_before_persistence(self):
        with self.assertRaisesRegex(ValueError, "至少需要一个目标"):
            save_custom_scenario({"name": "空场景", "targets": []})

        self.assertFalse(self.scenario_file.exists())


if __name__ == "__main__":
    unittest.main()
