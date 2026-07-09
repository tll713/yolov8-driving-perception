from collections import Counter


VEHICLE_CLASSES = {"car", "bus", "truck"}
VULNERABLE_CLASSES = {"person", "bicycle", "motorcycle"}
SIGNAL_CLASSES = {"traffic light", "stop sign"}
RISK_ORDER = {"low": 0, "info": 1, "medium": 2, "high": 3}


def _risk_level(item):
    return item.get("risk", {}).get("level", item.get("risk_level", "low"))


def _risk_score(item):
    return item.get("risk", {}).get("score", item.get("risk_score", 0))


def _class_name(item):
    return item.get("class_name", "")


def _class_label(item):
    return item.get("class_name_cn") or item.get("class_name") or "目标"


def _risk_label(level):
    labels = {
        "high": "高风险",
        "medium": "中风险",
        "info": "交通提示",
        "low": "低风险",
    }
    return labels.get(level, level or "低风险")


def _max_risk_level(detections):
    max_level = "low"
    for item in detections:
        level = _risk_level(item)
        if RISK_ORDER.get(level, 0) > RISK_ORDER.get(max_level, 0):
            max_level = level
    return max_level


def _risk_counts(detections):
    counts = {"low": 0, "info": 0, "medium": 0, "high": 0}
    for item in detections:
        level = _risk_level(item)
        counts[level] = counts.get(level, 0) + 1
    return counts


def build_scene_summary(detections):
    total = len(detections)
    vehicle_count = sum(1 for item in detections if _class_name(item) in VEHICLE_CLASSES)
    vulnerable_count = sum(1 for item in detections if _class_name(item) in VULNERABLE_CLASSES)
    signal_count = sum(1 for item in detections if _class_name(item) in SIGNAL_CLASSES)
    lane_targets = [item for item in detections if float(item.get("lane_overlap") or 0) >= 0.35]
    close_targets = [item for item in detections if int(item.get("distance_score") or 0) >= 60]
    high_targets = [item for item in detections if _risk_level(item) == "high"]

    if total == 0:
        density_level = "空场景"
    elif total <= 2:
        density_level = "稀疏"
    elif total <= 6:
        density_level = "中等"
    else:
        density_level = "密集"

    if high_targets:
        scene_type = "前方高风险通行场景"
    elif vulnerable_count:
        scene_type = "弱势交通参与者混行场景"
    elif vehicle_count >= 3:
        scene_type = "多车辆跟驰场景"
    elif signal_count:
        scene_type = "交通信号提示场景"
    elif total:
        scene_type = "常规道路目标场景"
    else:
        scene_type = "未检测到显著目标"

    tags = []
    if lane_targets:
        tags.append("行驶路径占用")
    if close_targets:
        tags.append("近距离目标")
    if vulnerable_count:
        tags.append("行人/两轮车")
    if vehicle_count:
        tags.append("机动车")
    if signal_count:
        tags.append("交通标志/信号")
    if not tags:
        tags.append("低风险观察")

    primary_target = None
    if detections:
        primary = max(detections, key=lambda item: (RISK_ORDER.get(_risk_level(item), 0), _risk_score(item)))
        primary_target = {
            "class_name": _class_label(primary),
            "risk_level": _risk_level(primary),
            "risk_score": _risk_score(primary),
            "lane_overlap": primary.get("lane_overlap", 0),
            "distance_score": primary.get("distance_score", 0),
        }

    return {
        "scene_type": scene_type,
        "density_level": density_level,
        "total_objects": total,
        "vehicle_count": vehicle_count,
        "vulnerable_count": vulnerable_count,
        "signal_count": signal_count,
        "lane_target_count": len(lane_targets),
        "close_target_count": len(close_targets),
        "max_risk_level": _max_risk_level(detections),
        "tags": tags,
        "primary_target": primary_target,
    }


def build_decision_trace(detections):
    summary = build_scene_summary(detections)
    counts = _risk_counts(detections)
    primary = summary["primary_target"]
    trace = [
        {
            "step": "目标检测",
            "result": f"识别到 {summary['total_objects']} 个交通目标",
            "evidence": f"机动车 {summary['vehicle_count']}，弱势交通参与者 {summary['vulnerable_count']}，信号/标志 {summary['signal_count']}",
        },
        {
            "step": "行驶路径判断",
            "result": f"{summary['lane_target_count']} 个目标与自车路径重叠",
            "evidence": "通过目标框底部位置和透视行驶走廊估算路径占用",
        },
        {
            "step": "距离与类别加权",
            "result": f"{summary['close_target_count']} 个近距离目标",
            "evidence": "综合目标底部位置、面积占比、类别风险和置信度",
        },
        {
            "step": "风险分级",
            "result": f"高 {counts['high']} / 中 {counts['medium']} / 低 {counts['low']} / 提示 {counts['info']}",
            "evidence": f"当前最高等级：{_risk_label(summary['max_risk_level'])}",
        },
    ]
    if primary:
        trace.append(
            {
                "step": "主风险目标",
                "result": f"{primary['class_name']}，风险分 {primary['risk_score']}",
                "evidence": f"路径重叠 {round(float(primary['lane_overlap']) * 100)}%，距离分 {primary['distance_score']}",
            }
        )
    return trace


def build_demo_script(detections):
    summary = build_scene_summary(detections)
    primary = summary["primary_target"]
    script = [
        f"当前画面被判定为：{summary['scene_type']}，目标密度为{summary['density_level']}。",
        "系统先用 YOLOv8 完成目标检测，再根据自车行驶走廊、目标距离和类别风险进行综合评分。",
    ]
    if primary:
        script.append(
            f"主要风险来自 {primary['class_name']}，风险等级为{_risk_label(primary['risk_level'])}，风险分为 {primary['risk_score']}。"
        )
    else:
        script.append("当前没有明显交通目标，系统保持低风险观察状态。")
    if summary["vulnerable_count"]:
        script.append("检测到行人或两轮车时，系统会提高风险敏感度，演示时可强调弱势交通参与者保护。")
    if summary["lane_target_count"]:
        script.append("目标进入自车行驶路径后，风险会显著上升，这是本项目风险算法的核心判断依据。")
    return script[:5]


def build_safety_advice(detections):
    advice = []
    levels = [_risk_level(item) for item in detections]
    classes = {item.get("class_name", "") for item in detections}

    if "high" in levels:
        high_items = [
            _class_label(item)
            for item in detections
            if _risk_level(item) == "high"
        ]
        advice.append(
            {
                "level": "high",
                "message": f"前方存在高风险目标（{', '.join(high_items[:3])}），建议立即减速并保持避让空间。",
            }
        )

    if classes & VULNERABLE_CLASSES:
        advice.append(
            {
                "level": "medium",
                "message": "检测到行人或两轮车等弱势交通参与者，建议降低车速并持续观察其运动方向。",
            }
        )

    if classes & VEHICLE_CLASSES:
        advice.append(
            {
                "level": "medium",
                "message": "检测到机动车目标，建议保持安全车距，避免急加速或急变道。",
            }
        )

    if classes & SIGNAL_CLASSES:
        advice.append(
            {
                "level": "info",
                "message": "检测到交通信号或停止标志，建议结合道路规则确认通行状态。",
            }
        )

    if not advice:
        advice.append(
            {
                "level": "low",
                "message": "当前画面未发现明显高风险目标，建议保持正常观察和安全车速。",
            }
        )

    return advice[:4]


def build_dashboard(history_items):
    total_records = len(history_items)
    total_objects = sum(int(item.get("count") or item.get("total_objects") or 0) for item in history_items)
    high_risk_records = sum(1 for item in history_items if item.get("max_risk_level") == "high")
    inference_times = [
        float(item.get("inference_time_ms"))
        for item in history_items
        if item.get("inference_time_ms") not in (None, "")
    ]
    average_time = round(sum(inference_times) / len(inference_times), 2) if inference_times else 0

    class_counter = Counter()
    for item in history_items:
        for detection in item.get("detections", []) or []:
            class_name = detection.get("class_name_cn") or detection.get("class_name") or "unknown"
            class_counter[class_name] += 1

    return {
        "total_records": total_records,
        "total_objects": total_objects,
        "high_risk_records": high_risk_records,
        "high_risk_ratio": round(high_risk_records / total_records, 4) if total_records else 0,
        "average_inference_time_ms": average_time,
        "top_classes": [
            {"class_name": class_name, "count": count}
            for class_name, count in class_counter.most_common(5)
        ],
    }
