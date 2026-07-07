from pathlib import Path

from backend.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    DEFAULT_MODEL_PATH,
    UPLOAD_DIR,
)
from backend.services.history_service import append_history
from detect import detect_image
from utils import save_upload


def _validate_confidence(confidence):
    if confidence < 0 or confidence > 1:
        raise ValueError("置信度阈值必须在 0 到 1 之间")
    return confidence


def _validate_file(upload, allowed_extensions, label):
    if not upload.filename:
        raise ValueError(f"请上传{label}文件")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in allowed_extensions:
        supported = "、".join(sorted(allowed_extensions))
        raise ValueError(f"{label}格式不支持，仅支持：{supported}")


def detect_uploaded_image(upload, confidence=0.5):
    _validate_file(upload, ALLOWED_IMAGE_EXTENSIONS, "图片")
    confidence = _validate_confidence(confidence)

    upload_path = save_upload(upload, upload_dir=UPLOAD_DIR)
    detections = detect_image(upload_path, model_path=DEFAULT_MODEL_PATH, confidence=confidence)
    result = {
        "type": "image",
        "filename": upload_path.name,
        "confidence": confidence,
        "count": len(detections),
        "detections": detections,
    }
    append_history(result)
    return result


def prepare_video_detection(upload):
    _validate_file(upload, ALLOWED_VIDEO_EXTENSIONS, "视频")
    upload_path = save_upload(upload, upload_dir=UPLOAD_DIR)
    return {
        "type": "video",
        "filename": upload_path.name,
        "status": "reserved",
    }
