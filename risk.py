RISK_LABELS = {
    "person": "行人",
    "car": "汽车",
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
RISK_PRIORITY = {"low": 0, "info": 1, "medium": 2, "high": 3}


def _bbox_features(bbox, image_width, image_height):
    x1, y1, x2, y2 = bbox
    box_area = max(0, x2 - x1) * max(0, y2 - y1)
    image_area = max(1, image_width * image_height)
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    return {
        "bbox_area": box_area,
        "center_x": round(center_x, 2),
        "center_y": round(center_y, 2),
        "area_ratio": round(box_area / image_area, 6),
        "in_center": image_width * 0.35 <= center_x <= image_width * 0.65,
        "in_lower": center_y >= image_height * 0.5,
    }


def assess_detection(detection, image_width, image_height):
    class_name = detection.get("class_name", "")
    bbox = detection.get("bbox", [0, 0, 0, 0])
    features = _bbox_features(bbox, image_width, image_height)
    label = RISK_LABELS.get(class_name, class_name or "目标")

    if class_name in TRAFFIC_INFO_CLASSES:
        return {
            "level": "info",
            "message": f"前方检测到{label}，请注意交通信息",
            "reason": f"检测到交通设施 {class_name}，作为驾驶提示信息展示",
        }

    if class_name in HIGH_RISK_CLASSES and features["in_center"] and features["in_lower"]:
        return {
            "level": "high",
            "message": f"高风险：前方中央区域检测到{label}",
            "reason": f"检测到 {class_name}，且目标中心位于画面下半部分的中央区域",
        }

    if class_name in VEHICLE_CLASSES and (
        features["area_ratio"] >= 0.15 or (features["in_center"] and features["in_lower"])
    ):
        return {
            "level": "high",
            "message": f"高风险：前方{label}距离较近",
            "reason": f"检测到 {class_name}，目标面积占比较大或位于前方关键区域",
        }

    if class_name in HIGH_RISK_CLASSES or class_name in VEHICLE_CLASSES:
        return {
            "level": "medium",
            "message": f"中风险：画面中检测到{label}",
            "reason": f"检测到道路参与者 {class_name}，但未处于高风险区域",
        }

    return {
        "level": "low",
        "message": f"低风险：检测到{label}",
        "reason": f"检测到 {class_name or 'unknown'}，当前规则判定风险较低",
    }


def assess_detections(detections, image_width, image_height):
    enriched = []
    for detection in detections:
        bbox = detection.get("bbox", [0, 0, 0, 0])
        features = _bbox_features(bbox, image_width, image_height)
        risk = assess_detection(detection, image_width, image_height)
        class_name = detection.get("class_name", "")
        enriched.append(
            {
                **detection,
                "class_name_cn": RISK_LABELS.get(class_name, class_name or "目标"),
                "bbox_area": features["bbox_area"],
                "center_x": features["center_x"],
                "center_y": features["center_y"],
                "area_ratio": features["area_ratio"],
                "risk": risk,
                "risk_level": risk["level"],
                "risk_message": risk["message"],
                "risk_reason": risk["reason"],
            }
        )
    return enriched


def summarize_risk(detections):
    counts = {"low": 0, "info": 0, "medium": 0, "high": 0}
    max_level = "low"

    for detection in detections:
        level = detection.get("risk", {}).get("level", "low")
        counts[level] = counts.get(level, 0) + 1
        if RISK_PRIORITY.get(level, 0) > RISK_PRIORITY.get(max_level, 0):
            max_level = level

    return {
        "max_risk_level": max_level,
        "risk_counts": counts,
    }
