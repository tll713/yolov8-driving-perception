from flask import Blueprint, jsonify, request

from backend.api_contract import build_error_response, build_success_response
from backend.services.simulation_service import list_simulation_presets, simulate_risk


simulation_bp = Blueprint("simulation", __name__)


@simulation_bp.get("/simulation/presets")
def simulation_presets():
    return jsonify(build_success_response({"items": list_simulation_presets()}))


@simulation_bp.post("/simulation/risk")
def simulation_risk():
    try:
        result = simulate_risk(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify(build_error_response(str(exc), 400)), 400
    except Exception as exc:
        return jsonify(build_error_response(f"仿真计算失败：{exc}", 500)), 500

    return jsonify(build_success_response(result))
