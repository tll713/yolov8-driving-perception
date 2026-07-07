from pathlib import Path

from risk import assess_detections


DEFAULT_MODEL_PATH = Path("models/yolov8s.pt")


def load_model(model_path=DEFAULT_MODEL_PATH):
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("未安装 ultralytics，请先执行 pip install -r requirements.txt") from exc

    return YOLO(str(model_path))


def detect_image(image_path, model_path=DEFAULT_MODEL_PATH, confidence=0.5):
    import cv2

    model = load_model(model_path)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("图片读取失败，请检查文件格式")

    height, width = image.shape[:2]
    results = model.predict(str(image_path), conf=confidence, verbose=False)
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

    return assess_detections(detections, width, height)
