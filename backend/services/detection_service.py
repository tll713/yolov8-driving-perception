from pathlib import Path

from backend.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    DEFAULT_MODEL_PATH,
    UPLOAD_DIR,
)
from backend.services.history_service import append_history
from backend.services.result_renderer import render_detection_image
from detect import detect_image
from risk import summarize_risk
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
    original_filename = upload.filename

    upload_path = save_upload(upload, upload_dir=UPLOAD_DIR)
    detection_result = detect_image(
        upload_path,
        model_path=DEFAULT_MODEL_PATH,
        confidence=confidence,
    )
    detections = detection_result["detections"]
    result_path = render_detection_image(upload_path, detections)
    risk_summary = summarize_risk(detections)

    result = {
        "type": "image",
        "original_filename": original_filename,
        "filename": upload_path.name,
        "upload_path": str(upload_path),
        "result_filename": result_path.name,
        "result_path": str(result_path),
        "model_name": DEFAULT_MODEL_PATH.stem,
        "confidence": confidence,
        "confidence_threshold": confidence,
        "image_width": detection_result["image_width"],
        "image_height": detection_result["image_height"],
        "count": len(detections),
        "total_objects": len(detections),
        "inference_time_ms": detection_result["inference_time_ms"],
        **risk_summary,
        "detections": detections,
    }
    append_history(result)
    return result


def prepare_video_detection(upload):
    _validate_file(upload, ALLOWED_VIDEO_EXTENSIONS, "视频")
    upload_path = save_upload(upload, upload_dir=UPLOAD_DIR)
    return {
        "type": "video",
        "original_filename": upload.filename,
        "filename": upload_path.name,
        "upload_path": str(upload_path),
        "status": "reserved",
    }
