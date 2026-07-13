import unittest
from pathlib import Path


class SimulationFrontendTest(unittest.TestCase):
    def setUp(self):
        self.component_source = Path("static/js/components.js").read_text(encoding="utf-8")
        self.app_source = Path("static/js/app.js").read_text(encoding="utf-8")
        self.template_source = Path("templates/index.html").read_text(encoding="utf-8")

    def test_dashboard_plays_backend_timeline(self):
        self.assertIn("frameIndex", self.component_source)
        self.assertIn("startPlayback", self.component_source)
        self.assertIn("this.timeline[this.frameIndex]", self.component_source)
        self.assertIn("风险时间曲线", self.component_source)
        self.assertIn("setPlaybackRate", self.component_source)
        self.assertIn("[0.5, 1, 2]", self.component_source)
        self.assertIn("nextTime - currentTime", self.component_source)

    def test_first_person_stage_uses_local_threejs_scene(self):
        self.assertIn("js/three.min.js", self.template_source)
        self.assertIn("js/DRACOLoader.js", self.template_source)
        self.assertIn("js/GLTFLoader.js", self.template_source)
        self.assertIn("new THREE.WebGLRenderer", self.component_source)
        self.assertIn('ref="simCanvas"', self.component_source)
        self.assertIn("syncThreeFrame", self.component_source)
        self.assertIn("configureThreeEnvironment", self.component_source)
        self.assertIn("loadThreeAssets", self.component_source)
        self.assertIn("setDecoderPath('/static/js/draco/')", self.component_source)
        self.assertIn("ferrari.glb", self.component_source)
        self.assertNotIn("soldier.glb", self.component_source)
        self.assertIn("target.world_position", self.component_source)
        self.assertIn("target.heading_rad", self.component_source)
        self.assertIn("threeTargetRenderPosition", self.component_source)
        self.assertIn("makeThreeTrafficLight({ withPole: false", self.component_source)
        self.assertNotIn("queueCar = this.makeThreeVehicle", self.component_source)
        self.assertIn("camera.position.set(0, 1.65, 6.2)", self.component_source)
        self.assertIn("new THREE.PlaneGeometry(42, 12)", self.component_source)
        self.assertIn("new THREE.PlaneGeometry(14, 190)", self.component_source)
        self.assertIn("new THREE.BoxGeometry(12, 0.05, 0.55)", self.component_source)
        self.assertIn("for (let segment = -3; segment <= 3; segment += 1)", self.component_source)
        self.assertIn("this.threeTrafficProps.forEach(detail => { detail.visible = !isBuiltInScenario })", self.component_source)
        self.assertIn("(this.threeSignalAnchorZ ?? z) + scenarioOffsetZ", self.component_source)
        self.assertIn("{ sedan: useSedan }", self.component_source)
        self.assertIn("model.rotation.y = -Number(target.heading_rad || 0)", self.component_source)
        self.assertIn("model.userData.brakeLightMaterial.emissiveIntensity", self.component_source)
        self.assertIn("if (target.class_name === 'bicycle') return this.makeThreeCyclist()", self.component_source)
        self.assertIn("const handlebar = new THREE.Mesh", self.component_source)
        self.assertIn("const torso = new THREE.Mesh", self.component_source)
        self.assertIn("const rearFender = new THREE.Mesh", self.component_source)
        self.assertIn("motorcycle.scale.setScalar(1.08)", self.component_source)
        self.assertNotIn("mixedIntersectionHudOffset", self.component_source)
        self.assertNotIn("marginLeft: hudOffset.x", self.component_source)
        self.assertNotIn("const closedLane", self.component_source)
        self.assertNotIn("warningTriangle", self.component_source)
        self.assertNotIn("waitingA =", self.component_source)
        self.assertNotIn("waitingB =", self.component_source)

    def test_cockpit_has_active_safety_feedback(self):
        self.assertIn("sim-wipers", self.component_source)
        self.assertIn("sim-adas-bar", self.component_source)
        self.assertIn("sim-aeb-alert", self.component_source)
        self.assertIn("自动紧急制动", self.component_source)

    def test_night_lighting_keeps_riders_visible(self):
        self.assertIn("hemi: 0.58, sun: 0.18, headlight: 0.9", self.component_source)

    def test_weather_and_scenario_parameters_are_sent_to_backend(self):
        self.assertIn("simulationWeatherOptions", self.app_source)
        self.assertIn("weather: simulationWeather.value", self.app_source)
        self.assertIn(':weather-options="simulationWeatherOptions"', self.template_source)

    def test_report_uses_simulation_metrics(self):
        for metric in (
            "min_ttc_sec",
            "first_warning_sec",
            "high_risk_duration_sec",
            "average_confidence",
            "collision",
            "aeb_activation_sec",
            "final_speed_kmh",
        ):
            self.assertIn(f"result.metrics.{metric}", self.component_source)

    def test_custom_scenario_editor_is_connected_to_persistence_api(self):
        self.assertIn("showScenarioEditor", self.component_source)
        self.assertIn("targetsJson", self.component_source)
        self.assertIn("eventsJson", self.component_source)
        self.assertIn("saveScenario", self.component_source)
        self.assertIn("/api/simulation/scenarios", self.app_source)
        self.assertIn("saveSimulationScenario", self.app_source)
        self.assertIn("deleteSimulationScenario", self.app_source)
        self.assertIn(':custom-scenarios="simulationCustomScenarios"', self.template_source)

    def test_aeb_comparison_runs_same_scenario_with_control_variable(self):
        self.assertIn("compareSimulationAeb", self.app_source)
        self.assertIn("simulationPayload(true)", self.app_source)
        self.assertIn("simulationPayload(false)", self.app_source)
        self.assertIn("comparisonResult.withAeb", self.component_source)
        self.assertIn("comparisonResult.withoutAeb", self.component_source)
        self.assertIn("是否避免碰撞", self.component_source)
        self.assertIn("碰撞速度降低", self.component_source)
        self.assertIn("停车距离差（启用 - 关闭）", self.component_source)
        self.assertIn("最小净距提升", self.component_source)
        self.assertIn("withMetrics.stopping_distance_m", self.component_source)
        self.assertIn("withoutMetrics.stopping_distance_m", self.component_source)
        self.assertIn("withStoppingDistance == null || withoutStoppingDistance == null", self.component_source)
        self.assertIn("关闭侧未停车", self.component_source)
        self.assertNotIn("Number(withoutMetrics.ego_distance_m", self.component_source)
        self.assertIn('@compare="compareSimulationAeb"', self.template_source)


if __name__ == "__main__":
    unittest.main()
