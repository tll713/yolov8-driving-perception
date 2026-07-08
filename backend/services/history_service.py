import json
from datetime import datetime

from backend.config import HISTORY_FILE
from backend.services.database_service import list_detection_history


def list_history():
    try:
        db_items = list_detection_history()
        if db_items:
            return db_items
    except Exception:
        pass

    if not HISTORY_FILE.exists():
        return []

    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def append_history(record):
    items = list_history()
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
