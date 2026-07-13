from backend.services.database_service import delete_detection_history, list_detection_history


def list_history(username=None):
    username = (username or "").strip()
    return list_detection_history(username=username or None)


def clear_history(username=None):
    username = (username or "").strip()
    return delete_detection_history(username=username or None)
