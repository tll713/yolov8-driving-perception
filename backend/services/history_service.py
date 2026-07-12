import json
from datetime import datetime

from backend.config import HISTORY_FILE
from backend.services.database_service import delete_detection_history, list_detection_history


def _read_json_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def list_history(username=None):
    username = (username or "").strip()
    try:
        db_items = list_detection_history(username=username or None)
        if db_items:
            return db_items
    except Exception:
        pass

    items = _read_json_history()
    if username:
        return [item for item in items if (item.get("username") or "").strip() == username]
    return items


def append_history(record):
    items = _read_json_history()
    items.insert(
        0,
        {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **record,
        },
    )
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(items[:50], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_history(username=None):
    username = (username or "").strip()
    try:
        delete_detection_history(username=username or None)
    except Exception:
        pass

    if username:
        items = [
            item
            for item in _read_json_history()
            if (item.get("username") or "").strip() != username
        ]
        HISTORY_FILE.parent.mkdir(exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    HISTORY_FILE.parent.mkdir(exist_ok=True)
    HISTORY_FILE.write_text("[]", encoding="utf-8")
