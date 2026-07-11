import unittest

from backend.services.simulation_service import list_simulation_presets, list_weather_profiles, simulate_risk


class SimulationServiceTest(unittest.TestCase):
    def test_list_presets_contains_demo_scenarios(self):
        presets = list_simulation_presets()
        keys = {item["key"] for item in presets}

        self.assertIn("normal_cruise", keys)
        self.assertIn("pedestrian_crossing", keys)
        self.assertIn("front_car_brake", keys)
        self.assertTrue(all(item["description"] for item in presets))

    def test_weather_profiles_are_available_for_dashboard_controls(self):
        weather_keys = {item["key"] for item in list_weather_profiles()}

        self.assertEqual(weather_keys, {"clear", "rain", "fog", "night"})

    def test_simulate_risk_returns_timeline_and_peak(self):
        result = simulate_risk({"scenario": "pedestrian_crossing", "duration_sec": 3, "step_sec": 1})

        self.assertEqual(result["scenario"], "pedestrian_crossing")
        self.assertEqual(len(result["timeline"]), 4)
        self.assertIn("score", result["peak_risk"])
        self.assertGreaterEqual(result["peak_risk"]["score"], 0)
        self.assertIn("min_ttc_sec", result["metrics"])
        self.assertIn("average_confidence", result["metrics"])
        self.assertTrue(result["summary"])

    def test_normal_cruise_stays_low_risk(self):
        result = simulate_risk({"scenario": "normal_cruise", "step_sec": 1})

        self.assertTrue(all(frame["max_risk_level"] == "low" for frame in result["timeline"]))
        self.assertIsNone(result["metrics"]["first_warning_sec"])
        self.assertFalse(result["metrics"]["collision"])

    def test_pedestrian_crossing_escalates_to_high_risk(self):
        result = simulate_risk({"scenario": "pedestrian_crossing", "step_sec": 0.5})
        levels = [frame["max_risk_level"] for frame in result["timeline"]]

        self.assertIn("medium", levels)
        self.assertIn("high", levels)
        self.assertGreater(result["metrics"]["high_risk_duration_sec"], 0)

    def test_aeb_reduces_speed_after_high_risk_activation(self):
        result = simulate_risk({"scenario": "pedestrian_crossing", "step_sec": 0.25})
        aeb_frames = [frame for frame in result["timeline"] if frame["aeb_active"]]

        self.assertTrue(aeb_frames)
        self.assertIsNotNone(result["metrics"]["aeb_activation_sec"])
        self.assertLess(result["metrics"]["final_speed_kmh"], result["ego_speed_kmh"])

    def test_bad_weather_reduces_simulated_detection_confidence(self):
        clear = simulate_risk({"scenario": "pedestrian_crossing", "weather": "clear"})
        fog = simulate_risk({"scenario": "pedestrian_crossing", "weather": "fog"})

        self.assertLess(fog["metrics"]["average_confidence"], clear["metrics"]["average_confidence"])

    def test_target_beyond_weather_perception_range_cannot_trigger_risk(self):
        result = simulate_risk(
            {
                "scenario": "fog-range-test",
                "weather": "fog",
                "duration_sec": 1,
                "step_sec": 1,
                "targets": [{"id": "far-car", "class_name": "car", "distance_m": 60, "lateral_m": 0}],
            }
        )

        target = result["timeline"][0]["targets"][0]
        self.assertFalse(target["detected"])
        self.assertEqual(target["confidence"], 0)
        self.assertEqual(result["timeline"][0]["max_risk_score"], 0)

    def test_rain_reduces_effective_braking_and_increases_stopping_distance(self):
        payload = {
            "scenario": "weather-braking-test",
            "ego_speed_kmh": 60,
            "duration_sec": 4,
            "step_sec": 0.1,
            "targets": [{"id": "car", "class_name": "car", "distance_m": 35, "lateral_m": 0}],
        }
        clear = simulate_risk({**payload, "weather": "clear"})
        rain = simulate_risk({**payload, "weather": "rain"})

        self.assertGreater(rain["metrics"]["ego_distance_m"], clear["metrics"]["ego_distance_m"])
        self.assertTrue(rain["metrics"]["collision"])
        self.assertFalse(clear["metrics"]["collision"])

    def test_aeb_uses_decision_delay_and_brake_ramp(self):
        result = simulate_risk(
            {
                "scenario": "aeb-response-test",
                "ego_speed_kmh": 50,
                "duration_sec": 2,
                "step_sec": 0.1,
                "aeb_delay_sec": 0.3,
                "aeb_ramp_sec": 0.4,
                "targets": [{"id": "car", "class_name": "car", "distance_m": 20, "lateral_m": 0}],
            }
        )
        active_frames = [frame for frame in result["timeline"] if frame["aeb_active"]]

        self.assertGreaterEqual(active_frames[0]["time_sec"], 0.3)
        self.assertGreater(active_frames[0]["brake_command_ratio"], 0)
        self.assertLess(active_frames[0]["brake_command_ratio"], 1)
        self.assertLess(active_frames[0]["brake_deceleration_mps2"], 6.5)

    def test_cpa_ttc_detects_lateral_crossing_conflict(self):
        result = simulate_risk(
            {
                "scenario": "crossing-cpa-test",
                "ego_speed_kmh": 36,
                "duration_sec": 1,
                "step_sec": 1,
                "targets": [
                    {
                        "id": "person",
                        "class_name": "person",
                        "distance_m": 10,
                        "lateral_m": -4,
                        "lateral_speed_mps": 4,
                    }
                ],
            }
        )
        risk = result["timeline"][0]["targets"][0]["risk"]

        self.assertEqual(risk["ttc_sec"], 1)
        self.assertEqual(risk["lateral_ttc_sec"], 0.55)
        self.assertEqual(risk["cpa_distance_m"], 0)

    def test_event_script_changes_target_motion_at_requested_time(self):
        result = simulate_risk(
            {
                "scenario": "event-test",
                "duration_sec": 2,
                "step_sec": 1,
                "targets": [
                    {"id": "lead", "class_name": "car", "distance_m": 40, "lateral_m": 0, "longitudinal_speed_mps": 10}
                ],
                "events": [
                    {"time_sec": 1, "target_id": "lead", "longitudinal_acceleration_mps2": -5}
                ],
            }
        )

        self.assertEqual(result["timeline"][0]["targets"][0]["longitudinal_acceleration_mps2"], 0)
        self.assertEqual(result["timeline"][1]["targets"][0]["longitudinal_acceleration_mps2"], -5)
        self.assertEqual(result["timeline"][2]["targets"][0]["longitudinal_speed_mps"], 5)

    def test_following_target_reacts_to_leader_braking_after_delay(self):
        result = simulate_risk(
            {
                "scenario": "following-test",
                "duration_sec": 2,
                "step_sec": 0.5,
                "targets": [
                    {"id": "lead", "class_name": "car", "distance_m": 30, "lateral_m": 0, "longitudinal_speed_mps": 10},
                    {
                        "id": "follower",
                        "class_name": "car",
                        "distance_m": 15,
                        "lateral_m": 0,
                        "longitudinal_speed_mps": 10,
                        "follow_target_id": "lead",
                        "desired_gap_m": 2,
                        "time_headway_sec": 0.5,
                        "reaction_delay_sec": 0.5,
                    },
                ],
                "events": [
                    {"time_sec": 0.5, "target_id": "lead", "longitudinal_acceleration_mps2": -6}
                ],
            }
        )
        follower_acceleration = [
            next(target for target in frame["targets"] if target["id"] == "follower")[
                "longitudinal_acceleration_mps2"
            ]
            for frame in result["timeline"]
        ]

        self.assertEqual(follower_acceleration[1], 0)
        self.assertLess(follower_acceleration[2], 0)

    def test_timeline_exposes_world_pose_for_renderer(self):
        result = simulate_risk({"scenario": "motorcycle_cut_in", "duration_sec": 1, "step_sec": 1})
        target = result["timeline"][1]["targets"][0]

        self.assertEqual(len(target["world_position"]), 3)
        self.assertEqual(target["world_position"][0], target["lateral_m"])
        self.assertIsInstance(target["heading_rad"], float)
        self.assertEqual(result["coordinate_frame"]["unit"], "meter")

    def test_red_traffic_light_keeps_constraint_risk_at_medium_or_above(self):
        result = simulate_risk(
            {
                "ego_speed_kmh": 0,
                "duration_sec": 1,
                "step_sec": 1,
                "targets": [
                    {
                        "id": "light-test",
                        "class_name": "traffic light",
                        "distance_m": 50,
                        "lateral_m": 0,
                        "state": "red",
                    }
                ],
            }
        )

        self.assertGreaterEqual(result["timeline"][0]["max_risk_score"], 62)
        self.assertEqual(result["timeline"][0]["max_risk_level"], "medium")

    def test_invalid_speed_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_risk({"ego_speed_kmh": 180})

    def test_invalid_weather_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_risk({"weather": "snowstorm"})

    def test_invalid_brake_deceleration_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_risk({"brake_deceleration_mps2": 15})


if __name__ == "__main__":
    unittest.main()
