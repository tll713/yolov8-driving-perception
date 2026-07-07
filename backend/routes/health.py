from datetime import datetime

from flask import Blueprint, jsonify

from backend.api_contract import build_success_response


health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    return jsonify(
        build_success_response(
            {
                "status": "ok",
                "service": "yolov8-driving-perception",
                "time": datetime.now().isoformat(timespec="seconds"),
            }
        )
    )
