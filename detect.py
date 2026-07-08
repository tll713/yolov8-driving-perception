from pathlib import Path
from time import perf_counter

from backend.config import (
    DEFAULT_DEVICE,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_INFERENCE_MODE,
    DEFAULT_MODEL_PATH,
    DEFAULT_REFINE_CONFIDENCE,
    DEFAULT_REFINE_IMAGE_SIZE,
    DEFAULT_REFINE_MIN_SIZE,
)
from backend.services.model_service import get_model
from risk import assess_detections


def _read_image_size(image):
    height, width = image.shape[:2]
    return width, height


def _predict(model, image_path, confidence, image_size, device):
    predict_options = {
        "conf": confidence,
        "imgsz": image_size,
        "verbose": False,
    }
    if device is not None:
        predict_options["device"] = device

    started_at = perf_counter()
    results = model.predict(str(image_path), **predict_options)
    inference_time_ms = round((perf_counter() - started_at) * 1000, 2)
    return results, inference_time_ms


def _parse_detections(results):
    detections = []
    for result in results:
        names = result.names
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = names[class_id]
            score = float(box.conf[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            detections.append(
                {
                    "class_name": class_name,
                    "confidence": round(score, 4),
                    "bbox": [x1, y1, x2, y2],
                }
            )
    return detections


def _should_refine(detections, width, height, mode, refine_min_size, refine_confidence):
    if mode != "balanced":
        return False
    if max(width, height) < refine_min_size:
        return False
    if not detections:
        return True
    best_confidence = max(item["confidence"] for item in detections)
    return best_confidence < refine_confidence


def detect_image(
    image_path,
    model_path=DEFAULT_MODEL_PATH,
    confidence=0.5,
    image_size=DEFAULT_IMAGE_SIZE,
    inference_mode=DEFAULT_INFERENCE_MODE,
    refine_image_size=DEFAULT_REFINE_IMAGE_SIZE,
    refine_min_size=DEFAULT_REFINE_MIN_SIZE,
    refine_confidence=DEFAULT_REFINE_CONFIDENCE,
    device=DEFAULT_DEVICE,
):
    import cv2

    image_path = Path(image_path)
    model = get_model(model_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("图片读取失败，请检查文件格式")

    width, height = _read_image_size(image)
    results, inference_time_ms = _predict(model, image_path, confidence, image_size, device)
    detections = _parse_detections(results)
    refined = False
    inference_size = image_size

    if _should_refine(
        detections,
        width,
        height,
        inference_mode,
        refine_min_size,
        refine_confidence,
    ):
        refined_results, refine_time_ms = _predict(
            model,
            image_path,
            confidence,
            refine_image_size,
            device,
        )
        detections = _parse_detections(refined_results)
        inference_time_ms = round(inference_time_ms + refine_time_ms, 2)
        refined = True
        inference_size = refine_image_size

    return {
        "image_width": width,
        "image_height": height,
        "inference_time_ms": inference_time_ms,
        "inference_mode": inference_mode,
        "inference_size": inference_size,
        "refined": refined,
        "detections": assess_detections(detections, width, height),
    }
