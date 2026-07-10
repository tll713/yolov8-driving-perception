import math

from backend.simulation_config import CLASS_BASE_RISK, CLASS_LABELS, PRESET_SCENARIOS, WEATHER_PROFILES


LANE_HALF_WIDTH_M = 1.8
COLLISION_RADIUS_M = 2.2
MAX_CPA_HORIZON_SEC = 12
EVENT_FIELDS = {
    "longitudinal_speed_mps",
    "lateral_speed_mps",
    "longitudinal_acceleration_mps2",
    "lateral_acceleration_mps2",
    "heading_rad",
}
EVENT_FIELD_LIMITS = {
    "longitudinal_speed_mps": (0, 80),
    "lateral_speed_mps": (-20, 20),
    "longitudinal_acceleration_mps2": (-15, 10),
    "lateral_acceleration_mps2": (-10, 10),
    "heading_rad": (-math.tau, math.tau),
}


def list_simulation_presets():
    return [
        {
            "key": key,
            "name": preset["name"],
            "description": preset["description"],
            "weather": preset["weather"],
            "ego_speed_kmh": preset["ego_speed_kmh"],
            "duration_sec": preset["duration_sec"],
            "target_count": len(preset["targets"]),
        }
        for key, preset in PRESET_SCENARIOS.items()
    ]


def list_weather_profiles():
    return [
        {
            "key": key,
            "name": profile["name"],
            "max_perception_distance_m": profile["max_perception_distance_m"],
            "brake_efficiency": profile["brake_efficiency"],
        }
        for key, profile in WEATHER_PROFILES.items()
    ]


def _clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def _risk_level(score):
    if score >= 76:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _collision_metrics(distance_m, lateral_m, ego_speed_mps, target_speed_mps, lateral_speed_mps):
    relative_longitudinal_speed = target_speed_mps - ego_speed_mps
    relative_speed_sq = relative_longitudinal_speed**2 + lateral_speed_mps**2
    closing_speed_mps = max(0, -relative_longitudinal_speed)
    longitudinal_ttc = distance_m / closing_speed_mps if distance_m > 0 and closing_speed_mps > 0.1 else None

    if abs(lateral_m) <= LANE_HALF_WIDTH_M:
        lateral_ttc = 0
    elif lateral_m * lateral_speed_mps < 0 and abs(lateral_speed_mps) > 0.05:
        lateral_ttc = (abs(lateral_m) - LANE_HALF_WIDTH_M) / abs(lateral_speed_mps)
    else:
        lateral_ttc = None

    cpa_ttc = None
    cpa_distance = None
    if relative_speed_sq > 0.01:
        candidate = -(
            distance_m * relative_longitudinal_speed + lateral_m * lateral_speed_mps
        ) / relative_speed_sq
        if 0 <= candidate <= MAX_CPA_HORIZON_SEC:
            cpa_longitudinal = distance_m + relative_longitudinal_speed * candidate
            cpa_lateral = lateral_m + lateral_speed_mps * candidate
            cpa_distance = math.hypot(cpa_longitudinal, cpa_lateral)
            if cpa_distance <= COLLISION_RADIUS_M:
                cpa_ttc = candidate

    return {
        "ttc_sec": round(cpa_ttc, 2) if cpa_ttc is not None else None,
        "longitudinal_ttc_sec": round(longitudinal_ttc, 2) if longitudinal_ttc is not None else None,
        "lateral_ttc_sec": round(lateral_ttc, 2) if lateral_ttc is not None else None,
        "cpa_distance_m": round(cpa_distance, 2) if cpa_distance is not None else None,
        "relative_speed_mps": round(math.sqrt(relative_speed_sq), 2),
        "closing_speed_mps": round(closing_speed_mps, 2),
    }


def _score_target(target, state, distance_m, ego_speed_mps):
    class_name = target.get("class_name", "car")
    lateral_m = state["lateral_m"]
    motion = _collision_metrics(
        distance_m,
        lateral_m,
        ego_speed_mps,
        state["longitudinal_speed_mps"],
        state["lateral_speed_mps"],
    )
    lane_overlap = _clamp(1 - abs(lateral_m) / 2.2, 0, 1)
    distance_score = _clamp(round((1 - min(max(distance_m, 0), 60) / 60) * 28), 0, 28)
    lane_score = round(lane_overlap * 22)
    speed_score = _clamp(round(ego_speed_mps * 3.6 / 100 * 8), 0, 8)
    ttc = motion["ttc_sec"]

    if ttc is None:
        ttc_score = 0
    elif ttc <= 1.5:
        ttc_score = 35
    elif ttc <= 3:
        ttc_score = 27
    elif ttc <= 5:
        ttc_score = 16
    elif ttc <= 8:
        ttc_score = 6
    else:
        ttc_score = 0

    score = round(CLASS_BASE_RISK.get(class_name, 9) + distance_score + lane_score + speed_score + ttc_score)
    if motion["closing_speed_mps"] <= 0.1 and ttc is None:
        score -= 20
    if class_name in {"traffic light", "traffic_light"} and target.get("state") == "red" and distance_m > -2:
        score = max(score, 62)
    if lane_overlap < 0.15 and distance_m > 12:
        score -= 15
    if distance_m < -2:
        score = 0
    score = _clamp(score)

    return {
        "level": _risk_level(score),
        "score": score,
        "lane_overlap": round(lane_overlap, 3),
        "distance_score": distance_score,
        **motion,
    }


def _perception_state(target, distance_m, weather_profile):
    detected = 0 <= distance_m <= weather_profile["max_perception_distance_m"]
    if not detected:
        return False, 0

    class_name = target.get("class_name", "car")
    class_factor = 0.96 if class_name in {"car", "truck", "bus"} else 0.92
    distance_factor = max(0.72, 1 - min(distance_m, 80) * 0.0025)
    confidence = _clamp(class_factor * distance_factor * weather_profile["confidence_factor"], 0.35, 0.98)
    return True, round(confidence, 3)


def _advice_for(level, target):
    label = CLASS_LABELS.get(target.get("class_name"), target.get("class_name", "目标"))
    if level == "high":
        return f"{label}已进入高风险区域，建议立即减速并准备制动。"
    if level == "medium":
        return f"{label}存在潜在冲突，建议降低车速并保持观察。"
    return "当前冲突风险较低，保持安全车速和车距。"


def _default_payload(payload):
    requested_key = payload.get("scenario", "pedestrian_crossing")
    has_custom_targets = bool(payload.get("targets"))
    if requested_key in PRESET_SCENARIOS:
        preset = PRESET_SCENARIOS[requested_key]
        scenario_key = requested_key
    elif has_custom_targets:
        preset = {
            "name": payload.get("name", "自定义场景"),
            "description": payload.get("description", ""),
            "weather": "clear",
            "ego_speed_kmh": 35,
            "duration_sec": 5,
            "targets": [],
            "events": [],
        }
        scenario_key = requested_key or "custom"
    else:
        scenario_key = "pedestrian_crossing"
        preset = PRESET_SCENARIOS[scenario_key]

    return {
        **preset,
        **{key: value for key, value in payload.items() if value not in (None, "")},
        "scenario": scenario_key,
        "targets": payload.get("targets") or preset["targets"],
        "events": payload.get("events") if payload.get("events") is not None else ([] if has_custom_targets else preset.get("events", [])),
    }


def _number(value, field_name, minimum=None, maximum=None):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} 必须是数字") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field_name} 必须是有限数字")
    if minimum is not None and result < minimum:
        raise ValueError(f"{field_name} 不能小于 {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{field_name} 不能大于 {maximum}")
    return result


def _validate_and_build_targets(targets):
    if not isinstance(targets, list) or not targets:
        raise ValueError("场景至少需要一个目标")
    if len(targets) > 20:
        raise ValueError("单个场景最多支持 20 个目标")

    states = {}
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            raise ValueError("目标配置必须是对象")
        target_id = str(target.get("id") or f"target-{index + 1}")
        if target_id in states:
            raise ValueError("目标 id 不能重复")
        target["id"] = target_id
        states[target_id] = {
            "target": target,
            "longitudinal_m": _number(target.get("distance_m", 0), "目标距离", -50, 500),
            "lateral_m": _number(target.get("lateral_m", 0), "目标横向位置", -50, 50),
            "longitudinal_speed_mps": _number(target.get("longitudinal_speed_mps", 0), "目标纵向速度", 0, 80),
            "lateral_speed_mps": _number(target.get("lateral_speed_mps", 0), "目标横向速度", -20, 20),
            "commanded_longitudinal_acceleration_mps2": _number(
                target.get("longitudinal_acceleration_mps2", 0), "目标纵向加速度", -15, 10
            ),
            "lateral_acceleration_mps2": _number(
                target.get("lateral_acceleration_mps2", 0), "目标横向加速度", -10, 10
            ),
            "effective_longitudinal_acceleration_mps2": 0,
            "heading_rad": target.get("heading_rad"),
            "follow_hazard_since": None,
        }
    return states


def _prepare_events(config, states, duration_sec):
    events = list(config.get("events") or [])
    for target_id, state in states.items():
        for event in state["target"].get("events") or []:
            events.append({**event, "target_id": target_id})
    if len(events) > 100:
        raise ValueError("单个场景最多支持 100 个事件")

    prepared = []
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("事件配置必须是对象")
        target_id = str(event.get("target_id", ""))
        if target_id not in states:
            raise ValueError(f"事件引用了不存在的目标：{target_id}")
        time_sec = _number(event.get("time_sec"), "事件时间", 0, duration_sec)
        values = {}
        for field in EVENT_FIELDS:
            if field in event:
                minimum, maximum = EVENT_FIELD_LIMITS[field]
                values[field] = _number(event[field], f"事件字段 {field}", minimum, maximum)
        if not values:
            raise ValueError("事件至少需要修改一个运动字段")
        prepared.append({"time_sec": time_sec, "target_id": target_id, "values": values})
    return sorted(prepared, key=lambda item: item["time_sec"])


def _apply_event(event, states):
    state = states[event["target_id"]]
    for field, value in event["values"].items():
        if field == "longitudinal_acceleration_mps2":
            state["commanded_longitudinal_acceleration_mps2"] = _clamp(value, -15, 10)
        else:
            state[field] = value


def _apply_following_interactions(states, time_sec):
    for state in states.values():
        target = state["target"]
        state["effective_longitudinal_acceleration_mps2"] = state[
            "commanded_longitudinal_acceleration_mps2"
        ]
        if state["longitudinal_speed_mps"] <= 0 and state["effective_longitudinal_acceleration_mps2"] < 0:
            state["effective_longitudinal_acceleration_mps2"] = 0
        leader_id = target.get("follow_target_id")
        if not leader_id:
            continue
        leader = states.get(str(leader_id))
        if leader is None:
            raise ValueError(f"跟随目标不存在：{leader_id}")

        gap_m = leader["longitudinal_m"] - state["longitudinal_m"]
        desired_gap_m = _number(target.get("desired_gap_m", 6), "期望跟车距离", 1, 100)
        time_headway_sec = _number(target.get("time_headway_sec", 1.2), "跟车时距", 0.2, 5)
        reaction_delay_sec = _number(target.get("reaction_delay_sec", 0.5), "跟车反应延迟", 0, 3)
        max_deceleration = _number(target.get("max_deceleration_mps2", 6), "目标最大减速度", 0.5, 12)
        desired_gap_m += state["longitudinal_speed_mps"] * time_headway_sec
        hazard = gap_m < desired_gap_m or leader["effective_longitudinal_acceleration_mps2"] < -0.1

        if not hazard:
            state["follow_hazard_since"] = None
            continue
        if state["follow_hazard_since"] is None:
            state["follow_hazard_since"] = time_sec
        if time_sec - state["follow_hazard_since"] < reaction_delay_sec:
            continue

        closing_speed = max(0, state["longitudinal_speed_mps"] - leader["longitudinal_speed_mps"])
        gap_error = max(0, desired_gap_m - gap_m)
        requested_deceleration = closing_speed / time_headway_sec + gap_error / max(desired_gap_m, 1) * max_deceleration
        state["effective_longitudinal_acceleration_mps2"] = min(
            state["effective_longitudinal_acceleration_mps2"],
            -min(max_deceleration, requested_deceleration),
        )


def _target_heading(state):
    if state["heading_rad"] is not None:
        return round(float(state["heading_rad"]), 4)
    if abs(state["lateral_speed_mps"]) < 0.05:
        return 0
    return round(math.atan2(state["lateral_speed_mps"], max(state["longitudinal_speed_mps"], 0.1)), 4)


def _build_metrics(timeline, step_sec, ego_distance_m):
    target_states = [target for frame in timeline for target in frame["targets"]]
    ttc_values = [
        target["risk"]["ttc_sec"]
        for target in target_states
        if target["detected"] and target["risk"]["ttc_sec"] is not None
    ]
    confidences = [target["confidence"] for target in target_states if target["detected"]]
    warning_frames = [frame for frame in timeline if frame["max_risk_level"] in {"medium", "high"}]
    high_frames = [frame for frame in timeline if frame["max_risk_level"] == "high"]
    return {
        "min_ttc_sec": min(ttc_values) if ttc_values else None,
        "first_warning_sec": warning_frames[0]["time_sec"] if warning_frames else None,
        "high_risk_duration_sec": round(len(high_frames) * step_sec, 2),
        "average_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "missed_perception_frames": sum(not target["detected"] for target in target_states),
        "collision": any(target["collision"] for target in target_states),
        "ego_distance_m": round(ego_distance_m, 2),
    }


def simulate_risk(payload):
    config = _default_payload(payload or {})
    ego_speed_kmh = _number(config.get("ego_speed_kmh", 35), "自车速度", 0, 140)
    duration_sec = _number(config.get("duration_sec", 5), "仿真时长", 0.01, 30)
    step_sec = _number(config.get("step_sec", 0.25), "仿真步长", 0.01, 2)
    weather_key = config.get("weather", "clear")
    auto_brake = config.get("auto_brake", True)
    brake_deceleration_mps2 = _number(config.get("brake_deceleration_mps2", 6.5), "制动减速度", 0.1, 12)
    aeb_delay_sec = _number(config.get("aeb_delay_sec", 0.3), "AEB 感知决策延迟", 0, 2)
    aeb_ramp_sec = _number(config.get("aeb_ramp_sec", 0.4), "AEB 制动力爬升时间", 0, 3)

    if weather_key not in WEATHER_PROFILES:
        raise ValueError("不支持的天气类型")
    if not isinstance(auto_brake, bool):
        raise ValueError("auto_brake 必须是布尔值")

    targets = config.get("targets") or []
    target_states_by_id = _validate_and_build_targets(targets)
    events = _prepare_events(config, target_states_by_id, duration_sec)
    weather_profile = WEATHER_PROFILES[weather_key]
    timeline = []
    ego_distance_m = 0
    current_ego_speed_mps = ego_speed_kmh / 3.6
    high_risk_since = None
    aeb_trigger_time = None
    next_event_index = 0
    frame_count = int(duration_sec / step_sec) + 1

    for frame_index in range(frame_count):
        time_sec = round(frame_index * step_sec, 6)
        while next_event_index < len(events) and events[next_event_index]["time_sec"] <= time_sec + 1e-9:
            _apply_event(events[next_event_index], target_states_by_id)
            next_event_index += 1
        _apply_following_interactions(target_states_by_id, time_sec)

        target_states = []
        max_level = "low"
        max_score = 0
        primary_target = None
        for state in target_states_by_id.values():
            target = state["target"]
            distance_m = state["longitudinal_m"] - ego_distance_m
            detected, confidence = _perception_state(target, distance_m, weather_profile)
            risk = _score_target(target, state, distance_m, current_ego_speed_mps)
            if not detected:
                risk = {**risk, "level": "low", "score": 0, "perception_limited": True}
            collision = (
                abs(distance_m) <= 0.8 and risk["lane_overlap"] >= 0.5
            ) or (
                risk["ttc_sec"] is not None
                and risk["ttc_sec"] <= step_sec
                and risk["cpa_distance_m"] is not None
                and risk["cpa_distance_m"] <= COLLISION_RADIUS_M
            )
            world_position = [round(state["lateral_m"], 3), 0, round(-distance_m, 3)]
            target_state = {
                "id": target["id"],
                "class_name": target.get("class_name", "car"),
                "class_name_cn": CLASS_LABELS.get(target.get("class_name"), target.get("class_name", "目标")),
                "distance_m": round(distance_m, 2),
                "lateral_m": round(state["lateral_m"], 2),
                "longitudinal_speed_mps": round(state["longitudinal_speed_mps"], 2),
                "lateral_speed_mps": round(state["lateral_speed_mps"], 2),
                "longitudinal_acceleration_mps2": round(
                    state["effective_longitudinal_acceleration_mps2"], 2
                ),
                "detected": detected,
                "confidence": confidence,
                "world_position": world_position,
                "heading_rad": _target_heading(state),
                "collision": collision,
                "risk": risk,
            }
            target_states.append(target_state)
            if detected and risk["score"] > max_score:
                max_score = risk["score"]
                max_level = risk["level"]
                primary_target = target_state

        if max_level == "high":
            if high_risk_since is None:
                high_risk_since = time_sec
        elif aeb_trigger_time is None:
            high_risk_since = None

        if (
            auto_brake
            and aeb_trigger_time is None
            and high_risk_since is not None
            and time_sec - high_risk_since >= aeb_delay_sec
        ):
            aeb_trigger_time = high_risk_since + aeb_delay_sec

        brake_command_ratio = 0
        if aeb_trigger_time is not None and current_ego_speed_mps > 0:
            if aeb_ramp_sec == 0:
                brake_command_ratio = 1
            else:
                brake_command_ratio = _clamp((time_sec - aeb_trigger_time) / aeb_ramp_sec, 0, 1)
        effective_deceleration = (
            brake_deceleration_mps2 * weather_profile["brake_efficiency"] * brake_command_ratio
        )
        aeb_active = brake_command_ratio > 0
        timeline.append(
            {
                "frame_index": frame_index,
                "time_sec": round(time_sec, 2),
                "ego_speed_kmh": round(current_ego_speed_mps * 3.6, 2),
                "ego_world_position": [0, 0, 0],
                "ego_travel_distance_m": round(ego_distance_m, 3),
                "aeb_request_active": aeb_trigger_time is not None,
                "aeb_active": aeb_active,
                "brake_command_ratio": round(brake_command_ratio, 3),
                "commanded_brake_deceleration_mps2": brake_deceleration_mps2 if aeb_trigger_time is not None else 0,
                "brake_deceleration_mps2": round(effective_deceleration, 3),
                "max_risk_level": max_level,
                "max_risk_score": max_score,
                "primary_target": primary_target,
                "targets": target_states,
                "perception_fps": round(25 * weather_profile["fps_factor"] - len(targets) * 0.4, 1),
                "advice": _advice_for(max_level, primary_target or {}),
            }
        )

        next_ego_speed_mps = max(0, current_ego_speed_mps - effective_deceleration * step_sec)
        ego_distance_m += (current_ego_speed_mps + next_ego_speed_mps) / 2 * step_sec
        current_ego_speed_mps = next_ego_speed_mps
        for state in target_states_by_id.values():
            acceleration = state["effective_longitudinal_acceleration_mps2"]
            lateral_acceleration = state["lateral_acceleration_mps2"]
            next_target_speed = max(0, state["longitudinal_speed_mps"] + acceleration * step_sec)
            next_lateral_speed = state["lateral_speed_mps"] + lateral_acceleration * step_sec
            state["longitudinal_m"] += (
                state["longitudinal_speed_mps"] + next_target_speed
            ) / 2 * step_sec
            state["lateral_m"] += (state["lateral_speed_mps"] + next_lateral_speed) / 2 * step_sec
            state["longitudinal_speed_mps"] = next_target_speed
            state["lateral_speed_mps"] = next_lateral_speed

    peak = max(timeline, key=lambda item: item["max_risk_score"]) if timeline else None
    metrics = _build_metrics(timeline, step_sec, ego_distance_m)
    metrics["average_fps"] = round(
        sum(frame["perception_fps"] for frame in timeline) / len(timeline), 1
    ) if timeline else 0
    aeb_frames = [frame for frame in timeline if frame["aeb_active"]]
    metrics["aeb_activation_sec"] = aeb_frames[0]["time_sec"] if aeb_frames else None
    metrics["aeb_delay_sec"] = aeb_delay_sec
    metrics["aeb_ramp_sec"] = aeb_ramp_sec
    metrics["final_speed_kmh"] = timeline[-1]["ego_speed_kmh"] if timeline else ego_speed_kmh
    min_ttc_text = f"{metrics['min_ttc_sec']}s" if metrics["min_ttc_sec"] is not None else "无接近冲突"
    return {
        "scenario": config.get("scenario"),
        "scenario_name": config.get("name", "自定义场景"),
        "description": config.get("description", ""),
        "weather": weather_key,
        "weather_name": weather_profile["name"],
        "weather_physics": {
            "brake_efficiency": weather_profile["brake_efficiency"],
            "max_perception_distance_m": weather_profile["max_perception_distance_m"],
        },
        "coordinate_frame": {
            "name": "ego",
            "unit": "meter",
            "axes": {"x": "right", "y": "up", "z": "backward"},
        },
        "ego_speed_kmh": ego_speed_kmh,
        "duration_sec": duration_sec,
        "step_sec": step_sec,
        "target_count": len(targets),
        "auto_brake": auto_brake,
        "peak_risk": {
            "level": peak["max_risk_level"] if peak else "low",
            "score": peak["max_risk_score"] if peak else 0,
            "time_sec": peak["time_sec"] if peak else 0,
            "target": peak["primary_target"] if peak else None,
        },
        "metrics": metrics,
        "timeline": timeline,
        "summary": [
            f"场景：{config.get('name', '自定义场景')} / {weather_profile['name']}",
            f"最小 TTC：{min_ttc_text}",
            f"最高风险：{peak['max_risk_score'] if peak else 0} 分，出现在 {peak['time_sec'] if peak else 0}s",
        ],
    }
