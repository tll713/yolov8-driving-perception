from flask import Flask, jsonify

from backend.api_contract import API_ENDPOINTS, build_success_response
from backend.config import ensure_runtime_directories
from backend.routes.detections import detections_bp
from backend.routes.health import health_bp
from backend.routes.models import models_bp


def create_app():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
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
        from flask import render_template
        return render_template('index.html')

    @app.get("/test")
    def test_page():
        from flask import render_template
        return render_template('test.html')

    @app.get("/api")
    def api_index():
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
