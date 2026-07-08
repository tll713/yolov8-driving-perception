import platform
import time

from flask import Blueprint, jsonify, request

from backend.api_contract import build_success_response, build_error_response
from backend.services.history_service import list_history

admin_bp = Blueprint("admin", __name__)

_admins = []
_confidence_threshold = 0.5
_error_logs = []
_start_time = time.time()


def _add_error_log(level, message):
    from datetime import datetime
    _error_logs.insert(0, {
        "id": len(_error_logs) + 1,
        "level": level,
        "message": message,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    if len(_error_logs) > 200:
        _error_logs.pop()


@admin_bp.post("/admin/register")
def admin_register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or len(username) < 3 or len(username) > 20:
        return jsonify(build_error_response("用户名需3-20个字符", 2001)), 400
    if not email or "@" not in email:
        return jsonify(build_error_response("请输入有效的邮箱地址", 2002)), 400
    if not password or len(password) < 6:
        return jsonify(build_error_response("密码至少6个字符", 2003)), 400
    if any(a["username"] == username for a in _admins):
        return jsonify(build_error_response("管理员用户名已存在", 2004)), 409

    _admins.append({"username": username, "email": email, "password": password})
    return jsonify(build_success_response({"username": username}, "管理员注册成功"))


@admin_bp.post("/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(build_error_response("用户名和密码不能为空", 2005)), 400

    admin = next((a for a in _admins if a["username"] == username), None)
    if not admin or admin["password"] != password:
        return jsonify(build_error_response("管理员用户名或密码错误", 2006)), 401

    return jsonify(build_success_response({"username": username, "role": "admin"}, "登录成功"))


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
    records = list_history()
    return jsonify(build_success_response({"items": records, "total": len(records)}))


@admin_bp.delete("/admin/records/<int:record_id>")
def delete_record(record_id):
    records = list_history()
    if record_id < 0 or record_id >= len(records):
        return jsonify(build_error_response("记录不存在", 2020)), 404

    records.pop(record_id)
    from backend.config import HISTORY_FILE
    import json
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
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
                gpu_info = f"{torch.cuda.get_device_name(0)}"
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
        }

    return jsonify(build_success_response(status))


def _format_uptime():
    uptime = int(time.time() - _start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


@admin_bp.get("/admin/error-logs")
def get_error_logs():
    return jsonify(build_success_response({"items": _error_logs, "total": len(_error_logs)}))


@admin_bp.delete("/admin/error-logs/<int:log_id>")
def delete_error_log(log_id):
    global _error_logs
    _error_logs = [l for l in _error_logs if l["id"] != log_id]
    return jsonify(build_success_response(None, "日志已删除"))