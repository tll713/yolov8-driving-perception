CLASS_BASE_RISK = {
    "person": 34,
    "bicycle": 31,
    "motorcycle": 32,
    "car": 22,
    "truck": 28,
    "bus": 26,
    "traffic_light": 8,
}

CLASS_LABELS = {
    "person": "行人",
    "bicycle": "自行车",
    "motorcycle": "摩托车",
    "car": "汽车",
    "truck": "卡车",
    "bus": "公交车",
    "traffic_light": "交通信号灯",
}

PRESET_SCENARIOS = {
    "pedestrian_crossing": {
        "name": "行人横穿",
        "ego_speed_kmh": 35,
        "duration_sec": 5,
        "targets": [
            {"id": "p1", "class_name": "person", "distance_m": 28, "lateral_m": -3.2, "lateral_speed_mps": 1.05}
        ],
    },
    "front_car_brake": {
        "name": "前车急停",
        "ego_speed_kmh": 55,
        "duration_sec": 5,
        "targets": [
            {"id": "car1", "class_name": "car", "distance_m": 42, "lateral_m": 0.1, "longitudinal_speed_mps": -8}
        ],
    },
    "motorcycle_cut_in": {
        "name": "两轮车并线",
        "ego_speed_kmh": 45,
        "duration_sec": 5,
        "targets": [
            {
                "id": "m1",
                "class_name": "motorcycle",
                "distance_m": 30,
                "lateral_m": 2.7,
                "lateral_speed_mps": -0.75,
                "longitudinal_speed_mps": -1,
            }
        ],
    },
    "red_light": {
        "name": "红灯路口",
        "ego_speed_kmh": 30,
        "duration_sec": 4,
        "targets": [
            {"id": "light1", "class_name": "traffic_light", "distance_m": 24, "lateral_m": 0, "state": "red"}
        ],
    },
}


def list_simulation_presets():
    return [
        {
            "key": key,
            "name": preset["name"],
            "ego_speed_kmh": preset["ego_speed_kmh"],
            "duration_sec": preset["duration_sec"],
        }
        for key, preset in PRESET_SCENARIOS.items()
    ]


def _clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def _risk_level(score):
    if score >= 76:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _target_state(target, ego_speed_mps, time_sec):
    longitudinal_speed = float(target.get("longitudinal_speed_mps", 0))
    lateral_speed = float(target.get("lateral_speed_mps", 0))
    distance = max(0, float(target.get("distance_m", 0)) + (longitudinal_speed - ego_speed_mps) * time_sec)
    lateral = float(target.get("lateral_m", 0)) + lateral_speed * time_sec
    return distance, lateral


def _score_target(target, distance_m, lateral_m, ego_speed_kmh):
    class_name = target.get("class_name", "car")
    base_score = CLASS_BASE_RISK.get(class_name, 18)
    lane_overlap = _clamp(1 - abs(lateral_m) / 2.2, 0, 1)
    distance_score = _clamp(round((1 - min(distance_m, 60) / 60) * 38), 0, 38)
    lane_score = round(lane_overlap * 28)
    speed_score = _clamp(round(float(ego_speed_kmh) / 90 * 16), 0, 16)

    closing_speed = max(0.1, float(ego_speed_kmh) / 3.6 - float(target.get("longitudinal_speed_mps", 0)))
    ttc = round(distance_m / closing_speed, 2) if distance_m > 0 else 0
    ttc_score = 18 if ttc <= 2 else 10 if ttc <= 4 else 4 if ttc <= 7 else 0

    score = _clamp(round(base_score + distance_score + lane_score + speed_score + ttc_score))
    if class_name == "traffic_light" and target.get("state") == "red":
        score = max(score, 62)
    if lane_overlap < 0.15 and distance_m > 12:
        score = max(0, score - 18)

    return {
        "level": _risk_level(score),
        "score": score,
        "lane_overlap": round(lane_overlap, 3),
        "distance_score": distance_score,
        "ttc_sec": ttc,
    }


def _advice_for(level, target):
    label = CLASS_LABELS.get(target.get("class_name"), target.get("class_name", "目标"))
    if level == "high":
        return f"{label}已进入高风险区域，建议立即减速并准备制动。"
    if level == "medium":
        return f"{label}存在潜在冲突，建议降低车速并保持观察。"
    return "当前冲突风险较低，保持安全车速和车距。"


def _default_payload(payload):
    scenario_key = payload.get("scenario", "pedestrian_crossing")
    preset = PRESET_SCENARIOS.get(scenario_key, PRESET_SCENARIOS["pedestrian_crossing"])
    return {
        **preset,
        **{key: value for key, value in payload.items() if value not in (None, "")},
        "scenario": scenario_key,
        "targets": payload.get("targets") or preset["targets"],
    }


def simulate_risk(payload):
    config = _default_payload(payload or {})
    ego_speed_kmh = float(config.get("ego_speed_kmh", 35))
    ego_speed_mps = ego_speed_kmh / 3.6
    duration_sec = float(config.get("duration_sec", 5))
    step_sec = float(config.get("step_sec", 0.5))
    targets = config.get("targets") or []

    if duration_sec <= 0 or duration_sec > 30:
        raise ValueError("仿真时长必须在 0 到 30 秒之间")
    if step_sec <= 0 or step_sec > 2:
        raise ValueError("仿真步长必须在 0 到 2 秒之间")
    if ego_speed_kmh < 0 or ego_speed_kmh > 140:
        raise ValueError("自车速度必须在 0 到 140 km/h 之间")

    timeline = []
    frame_count = int(duration_sec / step_sec) + 1
    for frame_index in range(frame_count):
        time_sec = round(frame_index * step_sec, 2)
        target_states = []
        max_level = "low"
        max_score = 0
        primary_target = None

        for target in targets:
            distance_m, lateral_m = _target_state(target, ego_speed_mps, time_sec)
            risk = _score_target(target, distance_m, lateral_m, ego_speed_kmh)
            state = {
                "id": target.get("id", target.get("class_name", "target")),
                "class_name": target.get("class_name", "car"),
                "class_name_cn": CLASS_LABELS.get(target.get("class_name"), target.get("class_name", "目标")),
                "distance_m": round(distance_m, 2),
                "lateral_m": round(lateral_m, 2),
                "risk": risk,
            }
            target_states.append(state)
            if risk["score"] > max_score:
                max_score = risk["score"]
                max_level = risk["level"]
                primary_target = state

        timeline.append(
            {
                "frame_index": frame_index,
                "time_sec": time_sec,
                "ego_speed_kmh": ego_speed_kmh,
                "max_risk_level": max_level,
                "max_risk_score": max_score,
                "primary_target": primary_target,
                "targets": target_states,
                "advice": _advice_for(max_level, primary_target or {}),
            }
        )

    peak = max(timeline, key=lambda item: item["max_risk_score"]) if timeline else None
    return {
        "scenario": config.get("scenario"),
        "scenario_name": config.get("name", "自定义场景"),
        "ego_speed_kmh": ego_speed_kmh,
        "duration_sec": duration_sec,
        "step_sec": step_sec,
        "target_count": len(targets),
        "peak_risk": {
            "level": peak["max_risk_level"] if peak else "low",
            "score": peak["max_risk_score"] if peak else 0,
            "time_sec": peak["time_sec"] if peak else 0,
            "target": peak["primary_target"] if peak else None,
        },
        "timeline": timeline,
        "summary": [
            f"场景：{config.get('name', '自定义场景')}",
            f"自车速度：{round(ego_speed_kmh, 1)} km/h",
            f"最高风险：{peak['max_risk_score'] if peak else 0} 分，出现在 {peak['time_sec'] if peak else 0}s",
        ],
    }
