from pathlib import Path
from time import perf_counter

from backend.config import DEFAULT_MODEL_PATH
from backend.services.model_service import get_model
from risk import assess_detections


def detect_image(image_path, model_path=DEFAULT_MODEL_PATH, confidence=0.5):
    import cv2

    image_path = Path(image_path)
    model = get_model(model_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("图片读取失败，请检查文件格式")

    height, width = image.shape[:2]
    started_at = perf_counter()
    results = model.predict(str(image_path), conf=confidence, verbose=False)
    inference_time_ms = round((perf_counter() - started_at) * 1000, 2)
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

    return {
        "image_width": width,
        "image_height": height,
        "inference_time_ms": inference_time_ms,
        "detections": assess_detections(detections, width, height),
    }
