"""中心化错误日志服务 —— MySQL 优先，文件兜底，永不抛异常"""

import json
import os
from datetime import datetime
from threading import Lock

from backend.config import ERROR_LOG_FILE

from backend.services.database_service import (
    delete_all_error_logs as _db_delete_all_error_logs,
    delete_error_log_by_id as _db_delete_error_log_by_id,
    list_error_logs as _db_list_error_logs,
    mark_error_log_handled as _db_mark_error_log_handled,
    save_error_log as _db_save_error_log,
)

_FILE_LOCK = Lock()
_MAX_FILE_ENTRIES = 200


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_file_logs():
    """读取文件中的错误日志列表"""
    if not ERROR_LOG_FILE.exists():
        return []
    try:
        data = json.loads(ERROR_LOG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_file_logs(logs):
    """覆写错误日志文件（截断到最大条目数）"""
    ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    trimmed = logs[-_MAX_FILE_ENTRIES:]
    ERROR_LOG_FILE.write_text(
        json.dumps(trimmed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _next_file_id(logs):
    """生成下一个文件端递增 ID"""
    if not logs:
        return 1
    return max((entry.get("id", 0) for entry in logs), default=0) + 1


def log_error(
    level="ERROR",
    source="system",
    message="",
    error_type="",
    request_path="",
    request_method="",
    username="",
    status_code=None,
    stack_trace="",
):
    """写入错误日志 —— 优先 MySQL，失败时降级写入 JSON 文件。永不抛异常"""
    try:
        _db_save_error_log(
            level=level,
            source=source,
            message=message,
            error_type=error_type,
            request_path=request_path or "",
            request_method=request_method or "",
            username=(username or "").strip(),
            status_code=status_code,
            stack_trace=stack_trace or "",
        )
        return
    except Exception:
        pass

    # MySQL 不可用 → 降级写入本地 JSON 兜底文件
    try:
        entry = {
            "id": 0,
            "level": level or "ERROR",
            "source": source or "system",
            "error_type": error_type or "",
            "message": message or "",
            "request_path": request_path or "",
            "request_method": request_method or "",
            "username": (username or "").strip(),
            "status_code": status_code,
            "stack_trace": stack_trace or "",
            "handled": 0,
            "created_at": _now(),
            "_source": "file",
        }
        with _FILE_LOCK:
            logs = _read_file_logs()
            entry["id"] = _next_file_id(logs)
            logs.append(entry)
            _write_file_logs(logs)
    except Exception:
        pass


def get_error_logs(limit=200):
    """获取错误日志列表 —— DB 优先，DB 不可用时返回文件数据"""
    try:
        return _db_list_error_logs(limit=limit)
    except Exception:
        pass

    try:
        logs = _read_file_logs()
        return list(reversed(logs[-limit:]))
    except Exception:
        return []


def delete_error_log(log_id):
    """删除单条错误日志。DB 优先，文件兜底。返回是否删除成功"""
    db_deleted = False
    file_deleted = False

    try:
        _db_delete_error_log_by_id(log_id)
        db_deleted = True
    except Exception:
        pass

    # 同时尝试从文件中删除
    try:
        with _FILE_LOCK:
            logs = _read_file_logs()
            before = len(logs)
            logs = [entry for entry in logs if entry.get("id") != log_id]
            if len(logs) < before:
                _write_file_logs(logs)
                file_deleted = True
    except Exception:
        pass

    return db_deleted or file_deleted


def delete_all_error_logs():
    """清空所有错误日志"""
    try:
        _db_delete_all_error_logs()
    except Exception:
        pass

    try:
        with _FILE_LOCK:
            _write_file_logs([])
    except Exception:
        pass


def mark_error_handled(log_id):
    """标记错误日志为已处理 —— DB 优先，文件兜底。返回是否操作成功"""
    db_ok = False
    file_ok = False

    try:
        db_ok = _db_mark_error_log_handled(log_id)
    except Exception:
        pass

    try:
        with _FILE_LOCK:
            logs = _read_file_logs()
            for entry in logs:
                if entry.get("id") == log_id:
                    entry["handled"] = 1
                    _write_file_logs(logs)
                    file_ok = True
                    break
    except Exception:
        pass

    return db_ok or file_ok
