from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"
LOG_DIR = BASE_DIR / "logs"
MODEL_DIR = BASE_DIR / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "yolov8s.pt"
HISTORY_FILE = LOG_DIR / "detection_history.json"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
DEFAULT_CONFIDENCE = 0.5


def ensure_runtime_directories():
    for folder in [UPLOAD_DIR, RESULT_DIR, LOG_DIR, MODEL_DIR]:
        folder.mkdir(exist_ok=True)
