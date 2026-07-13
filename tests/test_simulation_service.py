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
        self.assertEqual([frame["time_sec"] for frame in result["timeline"]], [0, 0.75, 1, 2, 3])
        self.assertIn("score", result["peak_risk"])
        self.assertGreaterEqual(result["peak_risk"]["score"], 0)
        self.assertIn("min_ttc_sec", result["metrics"])
        self.assertIn("average_confidence", result["metrics"])
        self.assertTrue(result["summary"])

    def test_custom_scenario_with_empty_targets_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "至少需要一个目标"):
            simulate_risk({"scenario": "custom:empty", "targets": []})

    def test_unknown_scenario_without_targets_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不支持的仿真场景"):
            simulate_risk({"scenario": "missing-scenario"})

    def test_timeline_includes_exact_duration_when_step_does_not_divide_evenly(self):
        result = simulate_risk(
            {
                "scenario": "timeline-end-test",
                "ego_speed_kmh": 36,
                "duration_sec": 1,
                "step_sec": 0.3,
                "auto_brake": False,
                "targets": [{"id": "far-car", "class_name": "car", "distance_m": 500}],
            }
        )

        self.assertEqual([frame["time_sec"] for frame in result["timeline"]], [0, 0.3, 0.6, 0.9, 1])
        self.assertEqual(result["metrics"]["ego_distance_m"], 10)

    def test_normal_cruise_stays_low_risk(self):
        result = simulate_risk({"scenario": "normal_cruise", "step_sec": 1})

        self.assertTrue(all(frame["max_risk_level"] == "low" for frame in result["timeline"]))
        self.assertIsNone(result["metrics"]["first_warning_sec"])
        self.assertFalse(result["metrics"]["collision"])

    def test_mixed_intersection_keeps_pedestrian_clear_of_stopped_car(self):
        result = simulate_risk({"scenario": "mixed_intersection", "step_sec": 0.25})
        separations = []

        for frame in result["timeline"]:
            targets = {target["id"]: target for target in frame["targets"]}
            separations.append(abs(targets["mix-car"]["distance_m"] - targets["mix-person"]["distance_m"]))

        self.assertGreaterEqual(min(separations), 3.5)
        self.assertFalse(result["metrics"]["collision"])

    def test_motorcycle_cut_in_starts_in_right_lane_and_merges_to_center(self):
        result = simulate_risk({"scenario": "motorcycle_cut_in", "step_sec": 0.25})
        first_target = result["timeline"][0]["targets"][0]
        final_target = result["timeline"][-1]["targets"][0]

        self.assertEqual(first_target["lateral_m"], 4.2)
        self.assertAlmostEqual(final_target["lateral_m"], 0, delta=0.05)
        self.assertEqual(first_target["longitudinal_speed_mps"], 8.5)
        self.assertEqual(final_target["lateral_speed_mps"], 0)
        self.assertEqual(final_target["heading_rad"], 0)
        self.assertIn("medium", [frame["max_risk_level"] for frame in result["timeline"]])
        self.assertGreaterEqual(result["metrics"]["aeb_activation_sec"], 4)
        self.assertLessEqual(result["metrics"]["aeb_activation_sec"], 5)

        extended = simulate_risk({"scenario": "motorcycle_cut_in", "duration_sec": 7, "step_sec": 0.25})
        self.assertAlmostEqual(extended["timeline"][-1]["targets"][0]["lateral_m"], 0, delta=0.05)

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

    def test_predicted_collision_is_not_reported_as_actual_when_aeb_avoids_it(self):
        result = simulate_risk(
            {
                "scenario": "aeb-avoidance-test",
                "ego_speed_kmh": 36,
                "duration_sec": 1,
                "step_sec": 1,
                "brake_deceleration_mps2": 12,
                "aeb_delay_sec": 0,
                "aeb_ramp_sec": 0,
                "targets": [{"id": "car", "class_name": "car", "distance_m": 10, "lateral_m": 0}],
            }
        )

        first_target = result["timeline"][0]["targets"][0]
        self.assertTrue(first_target["collision_predicted"])
        self.assertFalse(first_target["collision"])
        self.assertFalse(result["metrics"]["collision"])
        self.assertIsNone(result["metrics"]["collision_time_sec"])

    def test_actual_collision_is_recorded_when_motion_crosses_collision_zone(self):
        result = simulate_risk(
            {
                "scenario": "actual-collision-test",
                "ego_speed_kmh": 36,
                "duration_sec": 1,
                "step_sec": 1,
                "auto_brake": False,
                "targets": [{"id": "car", "class_name": "car", "distance_m": 5, "lateral_m": 0}],
            }
        )

        self.assertFalse(result["timeline"][0]["targets"][0]["collision"])
        self.assertTrue(result["timeline"][-1]["targets"][0]["collision"])
        self.assertTrue(result["metrics"]["collision"])
        self.assertAlmostEqual(result["metrics"]["collision_time_sec"], 0.08, places=2)

    def test_collision_envelope_matches_vehicle_dimensions(self):
        result = simulate_risk(
            {
                "scenario": "vehicle-envelope-test",
                "ego_speed_kmh": 0,
                "duration_sec": 0.1,
                "step_sec": 0.1,
                "auto_brake": False,
                "targets": [{"id": "car", "class_name": "car", "distance_m": 4.1, "lateral_m": 1.8}],
            }
        )

        self.assertTrue(result["timeline"][0]["targets"][0]["collision"])
        self.assertEqual(result["metrics"]["min_clearance_m"], 0)

    def test_minimum_clearance_includes_closest_point_between_output_frames(self):
        result = simulate_risk(
            {
                "scenario": "interval-clearance-test",
                "ego_speed_kmh": 0,
                "duration_sec": 2,
                "step_sec": 2,
                "auto_brake": False,
                "targets": [
                    {
                        "id": "crossing-car",
                        "class_name": "car",
                        "distance_m": 4.5,
                        "lateral_m": 4,
                        "lateral_speed_mps": -4,
                    }
                ],
            }
        )

        self.assertFalse(result["metrics"]["collision"])
        self.assertAlmostEqual(result["metrics"]["min_clearance_m"], 0.3, places=2)

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

        self.assertEqual(risk["ttc_sec"], 0.58)
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

    def test_event_between_regular_steps_is_applied_at_exact_time(self):
        result = simulate_risk(
            {
                "scenario": "fractional-event-test",
                "duration_sec": 1,
                "step_sec": 0.5,
                "auto_brake": False,
                "targets": [
                    {
                        "id": "person",
                        "class_name": "person",
                        "distance_m": 20,
                        "lateral_m": -4,
                    }
                ],
                "events": [
                    {"time_sec": 0.75, "target_id": "person", "lateral_speed_mps": 2}
                ],
            }
        )

        frames = {frame["time_sec"]: frame for frame in result["timeline"]}
        self.assertEqual(list(frames), [0, 0.5, 0.75, 1])
        self.assertEqual(frames[0.75]["targets"][0]["lateral_m"], -4)
        self.assertEqual(frames[0.75]["targets"][0]["lateral_speed_mps"], 2)
        self.assertEqual(frames[1]["targets"][0]["lateral_m"], -3.5)

    def test_aeb_trigger_uses_stopping_distance_components(self):
        result = simulate_risk(
            {
                "scenario": "stopping-distance-aeb-test",
                "ego_speed_kmh": 36,
                "duration_sec": 1,
                "step_sec": 0.5,
                "brake_deceleration_mps2": 5,
                "aeb_delay_sec": 0.5,
                "aeb_ramp_sec": 0,
                "aeb_safety_margin_m": 2,
                "targets": [{"id": "car", "class_name": "car", "distance_m": 16, "lateral_m": 0}],
            }
        )

        reason = result["metrics"]["aeb_trigger_reason"]
        self.assertEqual(result["metrics"]["aeb_request_sec"], 0)
        self.assertEqual(result["metrics"]["aeb_activation_sec"], 0.5)
        self.assertEqual(reason["type"], "stopping_distance")
        self.assertEqual(reason["reaction_distance_m"], 5)
        self.assertEqual(reason["braking_distance_m"], 10)
        self.assertEqual(reason["collision_buffer_m"], 4.2)
        self.assertEqual(reason["safety_margin_m"], 2)
        self.assertEqual(reason["required_distance_m"], 21.2)

    def test_aeb_does_not_trigger_for_same_lane_target_moving_away(self):
        result = simulate_risk(
            {
                "scenario": "opening-gap-aeb-test",
                "ego_speed_kmh": 36,
                "duration_sec": 2,
                "step_sec": 0.25,
                "targets": [
                    {
                        "id": "faster-car",
                        "class_name": "car",
                        "distance_m": 8,
                        "lateral_m": 0,
                        "longitudinal_speed_mps": 12,
                    }
                ],
            }
        )

        self.assertIsNone(result["metrics"]["aeb_request_sec"])
        self.assertFalse(any(frame["aeb_active"] for frame in result["timeline"]))
        self.assertEqual(result["metrics"]["final_speed_kmh"], 36)

    def test_aeb_path_check_uses_the_same_rectangular_collision_envelope(self):
        result = simulate_risk(
            {
                "scenario": "lateral-envelope-aeb-test",
                "ego_speed_kmh": 36,
                "duration_sec": 2,
                "step_sec": 0.25,
                "targets": [
                    {
                        "id": "cut-in-car",
                        "class_name": "car",
                        "distance_m": 4,
                        "lateral_m": 3,
                        "longitudinal_speed_mps": 10,
                        "lateral_speed_mps": -1,
                    }
                ],
            }
        )

        self.assertEqual(result["metrics"]["aeb_request_sec"], 0)

    def test_accelerating_target_collision_is_checked_inside_large_step(self):
        result = simulate_risk(
            {
                "scenario": "accelerating-interval-collision-test",
                "ego_speed_kmh": 36,
                "duration_sec": 2,
                "step_sec": 2,
                "auto_brake": False,
                "targets": [
                    {
                        "id": "accelerating-car",
                        "class_name": "car",
                        "distance_m": 5,
                        "lateral_m": 0,
                        "longitudinal_speed_mps": 0,
                        "longitudinal_acceleration_mps2": 10,
                    }
                ],
            }
        )

        self.assertTrue(result["metrics"]["collision"])
        self.assertAlmostEqual(result["metrics"]["collision_time_sec"], 0.084, delta=0.01)
        self.assertEqual(result["metrics"]["min_clearance_m"], 0)

    def test_aeb_still_triggers_for_crossing_target_and_red_light(self):
        crossing = simulate_risk({"scenario": "pedestrian_crossing", "step_sec": 0.25})
        red_light = simulate_risk(
            {
                "scenario": "red-light-aeb-test",
                "ego_speed_kmh": 30,
                "duration_sec": 2,
                "step_sec": 0.25,
                "targets": [
                    {
                        "id": "red",
                        "class_name": "traffic light",
                        "distance_m": 10,
                        "lateral_m": 0,
                        "state": "red",
                    }
                ],
            }
        )

        self.assertIsNotNone(crossing["metrics"]["aeb_request_sec"])
        self.assertIsNotNone(red_light["metrics"]["aeb_request_sec"])

    def test_stopping_distance_is_actual_distance_until_full_stop(self):
        payload = {
            "scenario": "actual-stopping-distance-test",
            "ego_speed_kmh": 36,
            "step_sec": 0.1,
            "brake_deceleration_mps2": 10,
            "aeb_delay_sec": 0,
            "aeb_ramp_sec": 0,
            "targets": [{"id": "car", "class_name": "car", "distance_m": 15, "lateral_m": 0}],
        }
        stopped = simulate_risk({**payload, "duration_sec": 4})
        still_moving = simulate_risk({**payload, "duration_sec": 0.8})

        self.assertIsNotNone(stopped["metrics"]["stopping_distance_m"])
        self.assertAlmostEqual(stopped["metrics"]["stopping_distance_m"], 5, delta=0.15)
        self.assertIsNone(still_moving["metrics"]["stopping_distance_m"])

    def test_aeb_comparison_metrics_expose_avoidance_speed_distance_and_clearance(self):
        payload = {
            "scenario": "comparison-metrics-test",
            "ego_speed_kmh": 36,
            "duration_sec": 1.2,
            "step_sec": 0.1,
            "brake_deceleration_mps2": 12,
            "aeb_delay_sec": 0,
            "aeb_ramp_sec": 0,
            "targets": [{"id": "car", "class_name": "car", "distance_m": 12, "lateral_m": 0}],
        }
        with_aeb = simulate_risk({**payload, "auto_brake": True})
        without_aeb = simulate_risk({**payload, "auto_brake": False})

        self.assertFalse(with_aeb["metrics"]["collision"])
        self.assertTrue(without_aeb["metrics"]["collision"])
        self.assertEqual(without_aeb["metrics"]["collision_speed_kmh"], 36)
        self.assertGreater(with_aeb["metrics"]["min_clearance_m"], without_aeb["metrics"]["min_clearance_m"])
        self.assertGreater(without_aeb["metrics"]["ego_distance_m"], with_aeb["metrics"]["ego_distance_m"])
        self.assertIsNotNone(with_aeb["metrics"]["stopping_distance_m"])
        self.assertIsNone(without_aeb["metrics"]["stopping_distance_m"])

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
