from flask import Blueprint, jsonify

from backend.api_contract import build_success_response
from backend.config import (
    DEFAULT_DEVICE,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_INFERENCE_MODE,
    DEFAULT_MODEL_PATH,
    DEFAULT_REFINE_CONFIDENCE,
    DEFAULT_REFINE_IMAGE_SIZE,
    DEFAULT_REFINE_MIN_SIZE,
)


models_bp = Blueprint("models", __name__)


@models_bp.get("/models/current")
def current_model():
    return jsonify(
        build_success_response(
            {
                "name": DEFAULT_MODEL_PATH.name,
                "path": str(DEFAULT_MODEL_PATH),
                "exists": DEFAULT_MODEL_PATH.exists(),
                "inference_mode": DEFAULT_INFERENCE_MODE,
                "image_size": DEFAULT_IMAGE_SIZE,
                "refine_image_size": DEFAULT_REFINE_IMAGE_SIZE,
                "refine_min_size": DEFAULT_REFINE_MIN_SIZE,
                "refine_confidence": DEFAULT_REFINE_CONFIDENCE,
                "device": DEFAULT_DEVICE or "cpu",
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
