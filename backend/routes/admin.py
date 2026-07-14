import platform
import time
import traceback

from flask import Blueprint, jsonify, request

from backend.api_contract import build_error_response, build_success_response
from backend.services.database_service import (
    delete_detection_record,
    get_detection_result,
)
from backend.services.error_log_service import (
    delete_all_error_logs,
    delete_error_log,
    get_error_logs,
    log_error,
)
from backend.services.history_service import list_history
from backend.services.user_service import (
    UserServiceError,
    authenticate_admin,
    create_user_by_admin,
    delete_user_by_admin,
    list_users,
    update_user_by_admin,
)

admin_bp = Blueprint("admin", __name__)

_confidence_threshold = 0.5
_start_time = time.time()


ADMIN_LOG_CODES = {
    1001,
    1002,
    1003,
    1004,
    1005,
    1010,
    1013,
    2006,
    3001,
}


def _service_error_response(error, source="admin", username=""):
    code = getattr(error, "code", 0)
    if code in ADMIN_LOG_CODES:
        level = "ERROR" if code >= 3000 else "WARN"
        log_error(
            level=level,
            source=source,
            error_type=type(error).__name__,
            message=str(error),
            request_path=request.path,
            request_method=request.method,
            username=(username or "").strip(),
            status_code=_status_from_code(code),
            stack_trace=traceback.format_exc(),
        )
    return jsonify(build_error_response(str(error), error.code)), _status_from_code(error.code)


def _status_from_code(code):
    if code in {1004, 1005, 2004}:
        return 409
    if code in {1007, 1008, 1011, 1012, 2006}:
        return 401
    if code == 1010:
        return 404
    return 400


def _format_uptime():
    uptime = int(time.time() - _start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"



@admin_bp.post("/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    try:
        admin = authenticate_admin(data.get("username"), data.get("password"))
    except UserServiceError as exc:
        return _service_error_response(exc, "admin_login", data.get("username"))
    return jsonify(build_success_response(admin, "登录成功"))


@admin_bp.get("/admin/users")
def get_users():
    try:
        users = list_users()
    except UserServiceError as exc:
        return _service_error_response(exc, "admin_list_users")
    return jsonify(build_success_response({"items": users, "total": len(users)}))


@admin_bp.post("/admin/users")
def create_user():
    data = request.get_json(silent=True) or {}
    try:
        user = create_user_by_admin(
            data.get("username"),
            data.get("email"),
            data.get("password"),
            data.get("status", "active"),
        )
    except UserServiceError as exc:
        return _service_error_response(exc, "admin_create_user", data.get("username"))
    return jsonify(build_success_response(user, "用户已创建"))


@admin_bp.put("/admin/users/<username>")
def update_user(username):
    data = request.get_json(silent=True) or {}
    try:
        user = update_user_by_admin(username, data)
    except UserServiceError as exc:
        return _service_error_response(exc, "admin_update_user", username)
    return jsonify(build_success_response(user, "用户已更新"))


@admin_bp.delete("/admin/users/<username>")
def delete_user(username):
    try:
        delete_user_by_admin(username)
    except UserServiceError as exc:
        return _service_error_response(exc, "admin_delete_user", username)
    return jsonify(build_success_response(None, "用户已删除"))


@admin_bp.get("/admin/confidence")
def get_confidence():
    return jsonify(build_success_response({"confidence": _confidence_threshold}))


@admin_bp.post("/admin/confidence")
def set_confidence():
    global _confidence_threshold
    data = request.get_json(silent=True) or {}
    value = data.get("confidence")

    try:
        value = float(value)
    except (TypeError, ValueError):
        return jsonify(build_error_response("请输入有效的数值", 2010)), 400

    if value < 0:
        value = 0.0
    elif value > 1:
        value = 1.0

    _confidence_threshold = round(value, 2)
    return jsonify(build_success_response({"confidence": _confidence_threshold}, "置信度阈值已更新"))


@admin_bp.get("/admin/records")
def get_all_records():
    username = (request.args.get("username") or "").strip()
    try:
        records = list_history(username=username or None)
    except Exception as exc:
        log_error(source="admin_list_records", error_type=type(exc).__name__, message=str(exc), request_path=request.path, request_method=request.method, username=username, status_code=500, stack_trace=traceback.format_exc())
        return jsonify(build_error_response(f"查询检测记录失败：{exc}", 500)), 500
    return jsonify(build_success_response({"items": records, "total": len(records)}))


@admin_bp.get("/admin/records/<int:record_id>")
def get_record(record_id):
    try:
        record = get_detection_result(record_id)
    except Exception as exc:
        log_error(source="admin_get_record", error_type=type(exc).__name__, message=str(exc), request_path=request.path, request_method=request.method, username="", status_code=500, stack_trace=traceback.format_exc())
        return jsonify(build_error_response(f"查询检测记录失败：{exc}", 500)), 500

    if record is None:
        return jsonify(build_error_response("记录不存在", 2020)), 404
    return jsonify(build_success_response(record))


@admin_bp.delete("/admin/records/<int:record_id>")
def delete_record(record_id):
    try:
        deleted = delete_detection_record(record_id)
    except Exception as exc:
        log_error(source="admin_delete_record", error_type=type(exc).__name__, message=str(exc), request_path=request.path, request_method=request.method, username="", status_code=500, stack_trace=traceback.format_exc())
        return jsonify(build_error_response(f"删除检测记录失败：{exc}", 500)), 500

    if not deleted:
        return jsonify(build_error_response("记录不存在", 2020)), 404
    return jsonify(build_success_response(None, "记录已删除"))


@admin_bp.get("/admin/system-status")
def system_status():
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            disk_used = f"{disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB"
        except Exception:
            disk_percent = 0
            disk_used = "N/A"

        gpu_info = "N/A"
        try:
            import torch

            if torch.cuda.is_available():
                gpu_info = torch.cuda.get_device_name(0)
        except ImportError:
            pass

        status = {
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "memory_used": f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB",
            "disk_percent": disk_percent,
            "disk_used": disk_used,
            "gpu": gpu_info,
            "platform": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "uptime": _format_uptime(),
            "status": "running",
            "total_detections": len(list_history()),
        }
    except ImportError:
        status = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used": "N/A (psutil未安装)",
            "disk_percent": 0,
            "disk_used": "N/A",
            "gpu": "N/A",
            "platform": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "uptime": _format_uptime(),
            "status": "running",
            "total_detections": len(list_history()),
        }

    return jsonify(build_success_response(status))


@admin_bp.get("/admin/error-logs")
def get_error_logs_route():
    try:
        logs = get_error_logs()
    except Exception as exc:
        return jsonify(build_error_response(f"查询错误日志失败：{exc}", 500)), 500
    return jsonify(build_success_response({"items": logs, "total": len(logs)}))


@admin_bp.delete("/admin/error-logs/<int:log_id>")
def delete_error_log_route(log_id):
    try:
        success = delete_error_log(log_id)
    except Exception as exc:
        return jsonify(build_error_response(f"删除错误日志失败：{exc}", 500)), 500
    if not success:
        return jsonify(build_error_response("日志不存在", 404)), 404
    return jsonify(build_success_response(None, "日志已删除"))


@admin_bp.delete("/admin/error-logs")
def clear_error_logs_route():
    try:
        delete_all_error_logs()
    except Exception as exc:
        return jsonify(build_error_response(f"清空错误日志失败：{exc}", 500)), 500
    return jsonify(build_success_response(None, "所有日志已清空"))
