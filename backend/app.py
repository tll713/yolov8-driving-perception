from flask import Flask, jsonify

from backend.api_contract import API_ENDPOINTS, build_success_response
from backend.config import ensure_runtime_directories
from backend.routes.detections import detections_bp
from backend.routes.health import health_bp
from backend.routes.models import models_bp


def create_app():
    app = Flask(__name__)
    ensure_runtime_directories()

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(detections_bp, url_prefix="/api")
    app.register_blueprint(models_bp, url_prefix="/api")

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.get("/")
    def index():
        return jsonify(
            build_success_response(
                {
                    "name": "yolov8-driving-perception backend",
                    "api_prefix": "/api",
                    "endpoints": API_ENDPOINTS,
                }
            )
        )

    return app
