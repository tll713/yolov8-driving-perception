from flask import Blueprint, jsonify, request

from backend.api_contract import build_error_response, build_success_response
from backend.services.simulation_scenario_service import (
    delete_custom_scenario,
    list_custom_scenarios,
    save_custom_scenario,
)
from backend.services.simulation_service import list_simulation_presets, list_weather_profiles, simulate_risk


simulation_bp = Blueprint("simulation", __name__)


@simulation_bp.get("/simulation/presets")
def simulation_presets():
    return jsonify(
        build_success_response(
            {"items": list_simulation_presets(), "weather_options": list_weather_profiles()}
        )
    )


@simulation_bp.get("/simulation/scenarios")
def simulation_scenarios():
    return jsonify(build_success_response({"items": list_custom_scenarios()}))


@simulation_bp.post("/simulation/scenarios")
def save_simulation_scenario():
    try:
        scenario = save_custom_scenario(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify(build_error_response(str(exc), 400)), 400
    except Exception as exc:
        return jsonify(build_error_response(f"场景保存失败：{exc}", 500)), 500
    return jsonify(build_success_response(scenario, "场景已保存"))


@simulation_bp.delete("/simulation/scenarios/<scenario_id>")
def delete_simulation_scenario(scenario_id):
    try:
        deleted = delete_custom_scenario(scenario_id)
    except Exception as exc:
        return jsonify(build_error_response(f"场景删除失败：{exc}", 500)), 500
    if not deleted:
        return jsonify(build_error_response("场景不存在", 404)), 404
    return jsonify(build_success_response({"id": scenario_id}, "场景已删除"))


@simulation_bp.post("/simulation/risk")
def simulation_risk():
    try:
        result = simulate_risk(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify(build_error_response(str(exc), 400)), 400
    except Exception as exc:
        return jsonify(build_error_response(f"仿真计算失败：{exc}", 500)), 500

    return jsonify(build_success_response(result))
