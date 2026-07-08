import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


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
DEFAULT_INFERENCE_MODE = os.getenv("YOLO_INFERENCE_MODE", "balanced").strip().lower()
DEFAULT_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
DEFAULT_REFINE_IMAGE_SIZE = int(os.getenv("YOLO_REFINE_IMAGE_SIZE", "960"))
DEFAULT_REFINE_MIN_SIZE = int(os.getenv("YOLO_REFINE_MIN_SIZE", "1280"))
DEFAULT_REFINE_CONFIDENCE = float(os.getenv("YOLO_REFINE_CONFIDENCE", "0.45"))
DEFAULT_DEVICE = os.getenv("YOLO_DEVICE", "").strip() or None

DB_HOST = os.getenv("DB_HOST", "10.149.89.160")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "yolov8_driving")


def ensure_runtime_directories():
    for folder in [UPLOAD_DIR, RESULT_DIR, LOG_DIR, MODEL_DIR]:
        folder.mkdir(exist_ok=True)
