import logging
import os
import traceback
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request, send_from_directory

from backend.api_contract import API_ENDPOINTS, build_success_response
from backend.config import (
    APP_LOG_FILE,
    LOG_BACKUP_COUNT,
    LOG_DIR,
    LOG_LEVEL,
    LOG_MAX_BYTES,
    RESULT_DIR,
    ensure_runtime_directories,
)
from backend.routes.admin import admin_bp
from backend.routes.auth import auth_bp
from backend.routes.detections import detections_bp
from backend.routes.health import health_bp
from backend.routes.models import models_bp
from backend.routes.simulation import simulation_bp
from backend.services.model_service import warmup_model


class _ErrorLogHandler(logging.Handler):
    """将 ERROR 级别日志同步写入集中错误日志服务"""

    def emit(self, record):
        try:
            from backend.services.error_log_service import log_error

            log_error(
                level=record.levelname,
                source="python_logger",
                error_type=record.name,
                message=record.getMessage(),
                request_path=getattr(record, "request_path", ""),
                request_method=getattr(record, "request_method", ""),
                username=getattr(record, "username", ""),
                status_code=getattr(record, "status_code", None),
                stack_trace="",
            )
        except Exception:
            pass


def _configure_app_logging(app):
    """配置 Python logging：文件轮转 + 错误日志服务桥接。
    只配置应用级 logger，不动 root logger，保证 Flask/Werkzeug 启动信息正常输出到控制台。
    """
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)

    # 文件处理器（所有 INFO+ 日志写入 logs/app.log）
    file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s %(pathname)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # 错误日志服务桥接处理器（ERROR 级别同步到 DB/文件）
    error_handler = _ErrorLogHandler()
    error_handler.setLevel(logging.ERROR)

    # 只配置应用自身的 logger，不动 root logger（保留控制台默认输出）
    app_logger = logging.getLogger("yolov8")
    app_logger.setLevel(log_level)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(error_handler)

    # Flask 内部日志也接入文件
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)


def create_app():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    ensure_runtime_directories()
    _configure_app_logging(app)
    warmup_model()

    app.register_blueprint(admin_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(detections_bp, url_prefix="/api")
    app.register_blueprint(models_bp, url_prefix="/api")
    app.register_blueprint(simulation_bp, url_prefix="/api")

    # ---- 全局错误处理器 ----
    @app.errorhandler(404)
    def handle_404(exc):
        return jsonify(build_error_response("请求的资源不存在", 404)), 404

    @app.errorhandler(500)
    def handle_500(exc):
        try:
            from backend.services.error_log_service import log_error

            log_error(
                level="ERROR",
                source="flask_global",
                error_type=type(exc).__name__,
                message=str(exc),
                request_path=request.path,
                request_method=request.method,
                username="",
                status_code=500,
                stack_trace=traceback.format_exc(),
            )
        except Exception:
            pass
        return jsonify(build_error_response("服务器内部错误", 500)), 500

    @app.errorhandler(Exception)
    def handle_exception(exc):
        try:
            from backend.services.error_log_service import log_error

            status_code = getattr(exc, "code", 500)
            if not isinstance(status_code, int) or status_code < 100 or status_code > 599:
                status_code = 500

            log_error(
                level="ERROR",
                source="flask_global",
                error_type=type(exc).__name__,
                message=str(exc),
                request_path=request.path,
                request_method=request.method,
                username="",
                status_code=status_code,
                stack_trace=traceback.format_exc(),
            )
        except Exception:
            pass
        return jsonify(build_error_response(str(exc), status_code)), status_code

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.get("/")
    def index():
        from flask import render_template

        return render_template("index.html")

    @app.get("/login")
    def login_page():
        from flask import render_template

        return render_template("login.html")

    @app.get("/register")
    def register_page():
        from flask import render_template

        return render_template("register.html")


    @app.get("/admin")
    def admin_dashboard():
        from flask import render_template

        return render_template("admin.html")

    @app.get("/profile")
    def profile_page():
        from flask import render_template

        return render_template("profile.html")

    @app.get("/history")
    def history_page():
        from flask import render_template

        return render_template("history.html")

    @app.get("/risk-analysis")
    def risk_analysis_page():
        from flask import render_template

        return render_template("risk_analysis.html")

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

    @app.get("/results/<path:filename>")
    def result_file(filename):
        return send_from_directory(RESULT_DIR, filename)

    return app
