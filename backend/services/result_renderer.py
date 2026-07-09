from pathlib import Path

from backend.config import RESULT_DIR
from backend.services.lane_service import draw_lane_overlay


RISK_COLORS = {
    "low": (40, 170, 80),
    "info": (255, 170, 40),
    "medium": (0, 165, 255),
    "high": (0, 0, 255),
}


def render_detection_image(image_path, detections, result_dir=RESULT_DIR, lane_analysis=None):
    import cv2

    image_path = Path(image_path)
    result_dir = Path(result_dir)
    result_dir.mkdir(exist_ok=True)

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError("图片读取失败，无法生成检测结果图")

    image = draw_lane_overlay(image, lane_analysis)

    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]
        risk_level = detection.get("risk", {}).get("level", "low")
        color = RISK_COLORS.get(risk_level, RISK_COLORS["low"])
        label = f"{detection['class_name']} {detection['confidence']:.2f} {risk_level}"

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        label_y = max(20, y1 - 8)
        cv2.putText(
            image,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
            cv2.LINE_AA,
        )

    result_path = result_dir / f"{image_path.stem}_result{image_path.suffix}"
    cv2.imwrite(str(result_path), image)
    return result_path
