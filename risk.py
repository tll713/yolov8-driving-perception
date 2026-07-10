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

VULNERABLE_CLASSES = {"person", "bicycle", "motorcycle"}
VEHICLE_CLASSES = {"car", "bus", "truck"}
TRAFFIC_INFO_CLASSES = {"traffic light", "stop sign"}
RISK_PRIORITY = {"low": 0, "info": 1, "medium": 2, "high": 3}

CLASS_RISK_SCORE = {
    "person": 36,
    "bicycle": 34,
    "motorcycle": 34,
    "truck": 23,
    "bus": 21,
    "car": 16,
}


def _clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def _zone(center_x, center_y, image_width, image_height):
    horizontal = "center"
    if center_x < image_width * 0.33:
        horizontal = "left"
    elif center_x > image_width * 0.67:
        horizontal = "right"

    vertical = "middle"
    if center_y < image_height * 0.33:
        vertical = "upper"
    elif center_y > image_height * 0.66:
        vertical = "lower"

    return f"{vertical}-{horizontal}"


def _driving_corridor_bounds(y, image_width, image_height):
    y_ratio = _clamp(y / max(1, image_height), 0, 1)
    center = image_width * 0.5
    half_width_ratio = 0.12 + 0.28 * y_ratio
    half_width = image_width * half_width_ratio
    return center - half_width, center + half_width


def _lane_overlap(x1, x2, bottom_y, image_width, image_height):
    lane_left, lane_right = _driving_corridor_bounds(bottom_y, image_width, image_height)
    overlap = max(0, min(x2, lane_right) - max(x1, lane_left))
    box_width = max(1, x2 - x1)
    return round(_clamp(overlap / box_width, 0, 1), 4)


def _bbox_features(bbox, image_width, image_height):
    x1, y1, x2, y2 = bbox
    box_width = max(0, x2 - x1)
    box_height = max(0, y2 - y1)
    box_area = box_width * box_height
    image_area = max(1, image_width * image_height)
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    bottom_y = max(y1, y2)
    area_ratio = box_area / image_area
    lane_overlap = _lane_overlap(x1, x2, bottom_y, image_width, image_height)
    bottom_ratio = _clamp(bottom_y / max(1, image_height), 0, 1)

    distance_score = _clamp(round(bottom_ratio * 62 + min(area_ratio * 260, 28)))
    position_score = _clamp(round(lane_overlap * 36 + (12 if bottom_ratio >= 0.58 else 0)))
    proximity_score = _clamp(round(distance_score * 0.65 + position_score * 0.35))

    return {
        "bbox_area": box_area,
        "center_x": round(center_x, 2),
        "center_y": round(center_y, 2),
        "bottom_y": round(bottom_y, 2),
        "area_ratio": round(area_ratio, 6),
        "zone": _zone(center_x, center_y, image_width, image_height),
        "lane_overlap": lane_overlap,
        "distance_score": distance_score,
        "position_score": position_score,
        "proximity_score": proximity_score,
    }


def _confidence_score(confidence):
    return _clamp(round((confidence - 0.25) / 0.65 * 30), 0, 30)


def _score_detection(class_name, confidence, features):
    class_risk_score = CLASS_RISK_SCORE.get(class_name, 10)
    confidence_score = _confidence_score(confidence)
    raw_score = (
        class_risk_score
        + features["distance_score"] * 0.42
        + features["position_score"] * 0.58
        + confidence_score
    )

    if features["lane_overlap"] < 0.35:
        raw_score -= 20
    if class_name in VEHICLE_CLASSES and features["distance_score"] < 52:
        raw_score -= 12
    if class_name in VEHICLE_CLASSES and features["area_ratio"] < 0.045:
        raw_score -= 8
    if confidence < 0.4:
        raw_score -= 18

    return _clamp(round(raw_score))


def _level_from_score(class_name, score, lane_overlap, confidence, distance_score, area_ratio, zone):
    if class_name in TRAFFIC_INFO_CLASSES:
        return "info"

    if class_name in VEHICLE_CLASSES:
        is_center_path = zone.endswith("center")
        is_critical_vehicle = (
            score >= 88
            and distance_score >= 72
            and area_ratio >= 0.07
            and lane_overlap >= 0.58
            and confidence >= 0.55
            and is_center_path
        )
        if is_critical_vehicle:
            return "high"
        if score >= 56 and (distance_score >= 54 or lane_overlap >= 0.32):
            return "medium"
        return "low"

    is_close = distance_score >= 68 or area_ratio >= 0.13
    is_in_path = lane_overlap >= 0.52
    is_reliable = confidence >= 0.5

    if score >= 86 and is_close and is_in_path and is_reliable:
        return "high"
    if score >= 52 and (lane_overlap >= 0.28 or distance_score >= 52):
        return "medium"
    return "low"


def _reason_parts(class_name, confidence, features):
    parts = [f"检测到 {class_name or 'unknown'}"]
    if features["lane_overlap"] >= 0.65:
        parts.append("目标与自车行驶路径高度重叠")
    elif features["lane_overlap"] >= 0.35:
        parts.append("目标接近自车行驶路径")
    else:
        parts.append("目标主要位于侧向区域")

    if features["distance_score"] >= 68:
        parts.append("目标底部靠近画面下方，估计距离较近")
    elif features["distance_score"] >= 45:
        parts.append("目标处于中等距离")
    else:
        parts.append("目标距离相对较远")

    if features["area_ratio"] >= 0.12:
        parts.append("目标面积占比较大")
    if confidence < 0.4:
        parts.append("置信度偏低，风险等级已降权")
    return parts


def assess_detection(detection, image_width, image_height):
    class_name = detection.get("class_name", "")
    confidence = float(detection.get("confidence", 0))
    bbox = detection.get("bbox", [0, 0, 0, 0])
    features = _bbox_features(bbox, image_width, image_height)
    label = RISK_LABELS.get(class_name, class_name or "目标")

    if class_name in TRAFFIC_INFO_CLASSES:
        return {
            "level": "info",
            "score": 20,
            "class_risk_score": 0,
            "confidence_score": _confidence_score(confidence),
            "distance_score": features["distance_score"],
            "position_score": features["position_score"],
            "lane_overlap": features["lane_overlap"],
            "message": f"交通提示：前方检测到{label}",
            "reason": f"检测到交通设施 {class_name}，作为驾驶提示信息展示，不计入碰撞风险",
        }

    score = _score_detection(class_name, confidence, features)
    level = _level_from_score(
        class_name,
        score,
        features["lane_overlap"],
        confidence,
        features["distance_score"],
        features["area_ratio"],
        features["zone"],
    )
    reason = "；".join(_reason_parts(class_name, confidence, features))

    if level == "high":
        message = f"高风险：前方行驶路径内检测到{label}"
    elif level == "medium":
        message = f"中风险：周边道路区域检测到{label}"
    else:
        message = f"低风险：检测到{label}"

    return {
        "level": level,
        "score": score,
        "class_risk_score": CLASS_RISK_SCORE.get(class_name, 10),
        "confidence_score": _confidence_score(confidence),
        "distance_score": features["distance_score"],
        "position_score": features["position_score"],
        "lane_overlap": features["lane_overlap"],
        "message": message,
        "reason": reason,
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
                "bottom_y": features["bottom_y"],
                "area_ratio": features["area_ratio"],
                "zone": features["zone"],
                "lane_overlap": features["lane_overlap"],
                "distance_score": features["distance_score"],
                "position_score": features["position_score"],
                "proximity_score": features["proximity_score"],
                "risk": risk,
                "risk_level": risk["level"],
                "risk_score": risk["score"],
                "risk_message": risk["message"],
                "risk_reason": risk["reason"],
            }
        )
    return enriched


def summarize_risk(detections):
    counts = {"low": 0, "info": 0, "medium": 0, "high": 0}
    max_level = "low"
    max_score = 0

    for detection in detections:
        risk = detection.get("risk", {})
        level = risk.get("level", "low")
        score = risk.get("score", detection.get("risk_score", 0))
        counts[level] = counts.get(level, 0) + 1
        if RISK_PRIORITY.get(level, 0) > RISK_PRIORITY.get(max_level, 0):
            max_level = level
        max_score = max(max_score, score)

    return {
        "max_risk_level": max_level,
        "max_risk_score": max_score,
        "risk_counts": counts,
    }
