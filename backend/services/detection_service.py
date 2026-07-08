from pathlib import Path

from backend.config import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    DEFAULT_CONFIDENCE,
    DEFAULT_MODEL_PATH,
    RESULT_DIR,
    UPLOAD_DIR,
)
from backend.services.database_service import save_detection_result
from backend.services.history_service import append_history
from backend.services.result_renderer import render_detection_image
from detect import detect_image, load_model
from risk import assess_detection, summarize_risk
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
    try:
        result["record_id"] = save_detection_result(result)
    except Exception:
        result["database_saved"] = False
    else:
        result["database_saved"] = True
    append_history(result)
    return result


def detect_uploaded_video(upload, confidence=DEFAULT_CONFIDENCE):
    import cv2

    _validate_file(upload, ALLOWED_VIDEO_EXTENSIONS, "视频")
    confidence = _validate_confidence(confidence)
    upload_path = save_upload(upload, upload_dir=UPLOAD_DIR)

    cap = cv2.VideoCapture(str(upload_path))
    if not cap.isOpened():
        raise ValueError("视频文件无法打开，请检查格式")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    model = load_model()

    result_path = RESULT_DIR / f"{upload_path.stem}_result.mp4"
    RESULT_DIR.mkdir(exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(result_path), fourcc, fps, (width, height))

    all_detections = []
    frame_idx = 0
    sample_interval = max(1, total_frames // 10) if total_frames > 0 else 1

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            results = model.predict(frame, conf=confidence, verbose=False)
            frame_detections = []
            for result in results:
                names = result.names
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = names[class_id]
                    score = float(box.conf[0])
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                    det = {
                        "class_name": class_name,
                        "confidence": round(score, 4),
                        "bbox": [x1, y1, x2, y2],
                    }
                    det["risk"] = assess_detection(det, width, height)
                    frame_detections.append(det)

                    color_map = {
                        "high": (0, 0, 255),
                        "medium": (0, 165, 255),
                        "info": (255, 100, 0),
                        "low": (0, 255, 100),
                    }
                    color = color_map.get(det["risk"]["level"], (0, 255, 100))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{class_name} {score * 100:.0f}%"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
                    cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            for d in frame_detections:
                if not any(
                    existing["class_name"] == d["class_name"]
                    and existing["bbox"] == d["bbox"]
                    for existing in all_detections
                ):
                    all_detections.append(d)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    risk_summary = summarize_risk(all_detections)

    result = {
        "type": "video",
        "original_filename": upload.filename,
        "filename": upload_path.name,
        "upload_path": str(upload_path),
        "confidence": confidence,
        "count": len(all_detections),
        "detections": all_detections,
        "result_video": f"/results/{result_path.name}",
        **risk_summary,
    }
    append_history(result)
    return result
