from flask import Blueprint, jsonify

from backend.api_contract import build_success_response
from backend.config import DEFAULT_MODEL_PATH


models_bp = Blueprint("models", __name__)


@models_bp.get("/models/current")
def current_model():
    return jsonify(
        build_success_response(
            {
                "name": DEFAULT_MODEL_PATH.name,
                "path": str(DEFAULT_MODEL_PATH),
                "exists": DEFAULT_MODEL_PATH.exists(),
                "classes": [
                    "person",
                    "car",
                    "bus",
                    "truck",
                    "bicycle",
                    "motorcycle",
                    "traffic light",
                    "stop sign",
                ],
            }
        )
    )
