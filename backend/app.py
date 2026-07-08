from flask import Flask, jsonify

from backend.api_contract import API_ENDPOINTS, build_success_response
from backend.config import ensure_runtime_directories
from backend.routes.admin import admin_bp
from backend.routes.auth import auth_bp
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

    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
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

    @app.get("/login")
    def login_page():
        from flask import render_template
        return render_template('login.html')

    @app.get("/register")
    def register_page():
        from flask import render_template
        return render_template('register.html')

    @app.get("/admin/login")
    def admin_login_page():
        from flask import render_template
        return render_template('admin_login.html')

    @app.get("/admin/register")
    def admin_register_page():
        from flask import render_template
        return render_template('admin_register.html')

    @app.get("/admin")
    def admin_dashboard():
        from flask import render_template
        return render_template('admin.html')

    @app.get("/results/<path:filename>")
    def serve_result(filename):
        from flask import send_from_directory
        from backend.config import RESULT_DIR
        return send_from_directory(str(RESULT_DIR), filename)

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
