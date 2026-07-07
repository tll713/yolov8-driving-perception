RISK_LABELS = {
    "person": "行人",
    "car": "车辆",
    "bus": "公交车",
    "truck": "卡车",
    "bicycle": "自行车",
    "motorcycle": "摩托车",
    "traffic light": "交通信号灯",
    "stop sign": "停止标志",
}

HIGH_RISK_CLASSES = {"person", "bicycle", "motorcycle"}
VEHICLE_CLASSES = {"car", "bus", "truck"}
TRAFFIC_INFO_CLASSES = {"traffic light", "stop sign"}


def assess_detection(detection, image_width, image_height):
    class_name = detection.get("class_name", "")
    bbox = detection.get("bbox", [0, 0, 0, 0])
    x1, y1, x2, y2 = bbox
    box_area = max(0, x2 - x1) * max(0, y2 - y1)
    image_area = max(1, image_width * image_height)
    area_ratio = box_area / image_area
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2

    in_center = image_width * 0.35 <= center_x <= image_width * 0.65
    in_lower = center_y >= image_height * 0.5
    label = RISK_LABELS.get(class_name, class_name or "目标")

    if class_name in TRAFFIC_INFO_CLASSES:
        return {
            "level": "info",
            "message": f"前方检测到{label}，请注意交通信息",
        }

    if class_name in HIGH_RISK_CLASSES and in_center and in_lower:
        return {
            "level": "high",
            "message": f"高风险：前方中央区域检测到{label}",
        }

    if class_name in VEHICLE_CLASSES and (area_ratio >= 0.15 or (in_center and in_lower)):
        return {
            "level": "high",
            "message": f"高风险：前方{label}距离较近",
        }

    if class_name in HIGH_RISK_CLASSES or class_name in VEHICLE_CLASSES:
        return {
            "level": "medium",
            "message": f"中风险：画面中检测到{label}",
        }

    return {
        "level": "low",
        "message": f"低风险：检测到{label}",
    }


def assess_detections(detections, image_width, image_height):
    return [
        {
            **detection,
            "risk": assess_detection(detection, image_width, image_height),
        }
        for detection in detections
    ]
