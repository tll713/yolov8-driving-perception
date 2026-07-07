from pathlib import Path
from uuid import uuid4


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}


def ensure_directories():
    for folder in ["uploads", "results", "logs", "models"]:
        Path(folder).mkdir(exist_ok=True)


def allowed_file(filename):
    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_IMAGE_EXTENSIONS or suffix in ALLOWED_VIDEO_EXTENSIONS


def save_upload(file_storage, upload_dir="uploads"):
    upload_path = Path(upload_dir)
    upload_path.mkdir(exist_ok=True)
    suffix = Path(file_storage.filename).suffix.lower()
    filename = f"{uuid4().hex}{suffix}"
    target = upload_path / filename
    file_storage.save(target)
    return target
