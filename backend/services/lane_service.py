def _empty_lane_analysis(width=0, height=0):
    return {
        "status": "unknown",
        "status_label": "车道线不足",
        "direction": "unknown",
        "direction_label": "道路方向不明确",
        "confidence": 0,
        "lane_count": 0,
        "center_offset_ratio": 0,
        "lane_width_ratio": 0,
        "message": "未检测到稳定车道线，建议保持人工观察。",
        "lines": [],
        "image_width": width,
        "image_height": height,
    }


def _average_line(lines):
    if not lines:
        return None

    x1 = round(sum(line["x1"] for line in lines) / len(lines))
    y1 = round(sum(line["y1"] for line in lines) / len(lines))
    x2 = round(sum(line["x2"] for line in lines) / len(lines))
    y2 = round(sum(line["y2"] for line in lines) / len(lines))
    slope = sum(line["slope"] for line in lines) / len(lines)
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "slope": round(slope, 4),
    }


def _fit_lane_line(lines, y_bottom, y_top):
    if not lines:
        return None

    import numpy as np

    points_x = []
    points_y = []
    slopes = []
    for line in lines:
        points_x.extend([line["x1"], line["x2"]])
        points_y.extend([line["y1"], line["y2"]])
        slopes.append(line["slope"])

    if len(points_x) < 2:
        return _average_line(lines)

    slope, intercept = np.polyfit(points_y, points_x, 1)
    x_bottom = int(slope * y_bottom + intercept)
    x_top = int(slope * y_top + intercept)
    return {
        "x1": x_bottom,
        "y1": y_bottom,
        "x2": x_top,
        "y2": y_top,
        "slope": round(sum(slopes) / len(slopes), 4),
    }


def _line_x_at_y(line, y):
    if line is None:
        return None
    y_delta = line["y2"] - line["y1"]
    if abs(y_delta) < 1:
        return None
    ratio = (y - line["y1"]) / y_delta
    return line["x1"] + ratio * (line["x2"] - line["x1"])


def _direction_from_offset(center_offset_ratio, heading_offset_ratio=0):
    if heading_offset_ratio <= -0.055 or center_offset_ratio <= -0.16:
        return "left", "需要左转/左变道"
    if heading_offset_ratio >= 0.055 or center_offset_ratio >= 0.16:
        return "right", "需要右转/右变道"
    return "straight", "直线行驶"


def _message(direction_label, confidence, lane_count):
    if lane_count < 2:
        return f"{direction_label}，但当前只检测到单侧车道线，建议谨慎参考。"
    if confidence >= 70:
        return f"车道线稳定，系统判断当前道路趋势为：{direction_label}。"
    return f"车道线置信度中等，系统初步判断为：{direction_label}。"


def analyze_lane_image(image_or_path):
    import cv2
    import numpy as np

    if isinstance(image_or_path, (str, bytes)):
        image = cv2.imread(str(image_or_path))
    else:
        image = image_or_path

    if image is None:
        return _empty_lane_analysis()

    height, width = image.shape[:2]
    if width <= 0 or height <= 0:
        return _empty_lane_analysis(width, height)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 160)

    mask = np.zeros_like(edges)
    roi = np.array(
        [
            [
                (int(width * 0.08), height),
                (int(width * 0.42), int(height * 0.55)),
                (int(width * 0.58), int(height * 0.55)),
                (int(width * 0.92), height),
            ]
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(mask, roi, 255)
    cropped = cv2.bitwise_and(edges, mask)

    raw_lines = cv2.HoughLinesP(
        cropped,
        rho=1,
        theta=np.pi / 180,
        threshold=38,
        minLineLength=max(28, width // 14),
        maxLineGap=max(18, width // 28),
    )
    if raw_lines is None:
        return _empty_lane_analysis(width, height)

    left_lines = []
    right_lines = []
    for item in raw_lines:
        values = item[0] if hasattr(item[0], "__iter__") else item
        x1, y1, x2, y2 = [int(v) for v in values]
        if x2 == x1:
            continue
        slope = (y2 - y1) / (x2 - x1)
        if abs(slope) < 0.35:
            continue

        line = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "slope": slope}
        if slope < 0 and max(x1, x2) < width * 0.62:
            left_lines.append(line)
        elif slope > 0 and min(x1, x2) > width * 0.38:
            right_lines.append(line)

    y_bottom = int(height * 0.92)
    y_top = int(height * 0.56)
    left_line = _fit_lane_line(left_lines, y_bottom, y_top)
    right_line = _fit_lane_line(right_lines, y_bottom, y_top)
    lane_lines = [line for line in [left_line, right_line] if line]
    lane_count = len(lane_lines)
    if lane_count == 0:
        return _empty_lane_analysis(width, height)

    left_x = _line_x_at_y(left_line, y_bottom)
    right_x = _line_x_at_y(right_line, y_bottom)

    top_left_x = _line_x_at_y(left_line, y_top)
    top_right_x = _line_x_at_y(right_line, y_top)
    heading_offset_ratio = 0

    if left_x is not None and right_x is not None:
        lane_center = (left_x + right_x) / 2
        lane_width_ratio = abs(right_x - left_x) / width
        if top_left_x is not None and top_right_x is not None:
            top_center = (top_left_x + top_right_x) / 2
            heading_offset_ratio = round((top_center - lane_center) / width, 4)
    elif left_x is not None:
        lane_center = left_x + width * 0.25
        lane_width_ratio = 0
        if top_left_x is not None:
            heading_offset_ratio = round((top_left_x - left_x) / width, 4)
    else:
        lane_center = right_x - width * 0.25
        lane_width_ratio = 0
        if top_right_x is not None:
            heading_offset_ratio = round((top_right_x - right_x) / width, 4)

    center_offset_ratio = round((lane_center - width * 0.5) / width, 4)
    if lane_count < 2:
        center_offset_ratio = 0
        if abs(heading_offset_ratio) < 0.09:
            heading_offset_ratio = 0
    direction, direction_label = _direction_from_offset(center_offset_ratio, heading_offset_ratio)
    confidence = min(95, 30 + lane_count * 22 + min(len(left_lines) + len(right_lines), 10) * 3)

    return {
        "status": "detected",
        "status_label": "车道已检测",
        "direction": direction,
        "direction_label": direction_label,
        "confidence": confidence,
        "lane_count": lane_count,
        "center_offset_ratio": center_offset_ratio,
        "heading_offset_ratio": heading_offset_ratio,
        "lane_width_ratio": round(lane_width_ratio, 4),
        "message": _message(direction_label, confidence, lane_count),
        "lines": lane_lines,
        "image_width": width,
        "image_height": height,
    }


def draw_lane_overlay(frame, lane_analysis):
    import cv2

    if not lane_analysis or lane_analysis.get("status") != "detected":
        return frame

    overlay = frame.copy()
    color = (80, 220, 255)
    for line in lane_analysis.get("lines", []):
        cv2.line(
            overlay,
            (int(line["x1"]), int(line["y1"])),
            (int(line["x2"]), int(line["y2"])),
            color,
            5,
            cv2.LINE_AA,
        )

    height, width = frame.shape[:2]
    direction_text = {
        "straight": "LANE: STRAIGHT",
        "left": "LANE: TURN LEFT",
        "right": "LANE: TURN RIGHT",
    }.get(lane_analysis.get("direction"), "LANE: UNKNOWN")
    label = f"{direction_text}  CONF {lane_analysis.get('confidence', 0)}%"
    banner_left = 18
    banner_top = max(18, height - 88)
    banner_right = min(width - 18, banner_left + 520)
    banner_bottom = min(height - 18, banner_top + 58)
    cv2.rectangle(overlay, (banner_left, banner_top), (banner_right, banner_bottom), (10, 70, 105), -1)
    cv2.rectangle(overlay, (banner_left, banner_top), (banner_right, banner_bottom), (80, 220, 255), 2)
    cv2.putText(
        overlay,
        label,
        (banner_left + 16, banner_top + 37),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.95,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return cv2.addWeighted(overlay, 0.55, frame, 0.45, 0)
