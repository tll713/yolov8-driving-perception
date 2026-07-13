CLASS_BASE_RISK = {
    "person": 15,
    "bicycle": 13,
    "motorcycle": 14,
    "car": 10,
    "truck": 12,
    "bus": 11,
    "traffic light": 8,
    "traffic_light": 8,
    "stop sign": 8,
}

CLASS_LABELS = {
    "person": "行人",
    "bicycle": "自行车",
    "motorcycle": "摩托车",
    "car": "汽车",
    "truck": "卡车",
    "bus": "公交车",
    "traffic light": "交通信号灯",
    "traffic_light": "交通信号灯",
    "stop sign": "停止标志",
}

WEATHER_PROFILES = {
    "clear": {
        "name": "晴天",
        "confidence_factor": 1.0,
        "fps_factor": 1.0,
        "brake_efficiency": 1.0,
        "max_perception_distance_m": 120,
    },
    "rain": {
        "name": "雨天",
        "confidence_factor": 0.91,
        "fps_factor": 0.9,
        "brake_efficiency": 0.72,
        "max_perception_distance_m": 70,
    },
    "fog": {
        "name": "雾天",
        "confidence_factor": 0.82,
        "fps_factor": 0.84,
        "brake_efficiency": 0.86,
        "max_perception_distance_m": 35,
    },
    "night": {
        "name": "夜间",
        "confidence_factor": 0.86,
        "fps_factor": 0.88,
        "brake_efficiency": 0.92,
        "max_perception_distance_m": 55,
    },
}

PRESET_SCENARIOS = {
    "normal_cruise": {
        "name": "正常跟车",
        "description": "前车匀速行驶，用于展示低风险基线。",
        "weather": "clear",
        "ego_speed_kmh": 42,
        "duration_sec": 6,
        "targets": [
            {
                "id": "car0",
                "class_name": "car",
                "distance_m": 30,
                "lateral_m": 0,
                "longitudinal_speed_mps": 13,
            }
        ],
    },
    "pedestrian_crossing": {
        "name": "行人横穿",
        "description": "行人从左侧进入车道，自车持续接近冲突点。",
        "weather": "clear",
        "ego_speed_kmh": 35,
        "duration_sec": 5,
        "targets": [
            {
                "id": "p1",
                "class_name": "person",
                "distance_m": 28,
                "lateral_m": -3.2,
                "lateral_speed_mps": 0,
            }
        ],
        "events": [
            {"time_sec": 0.75, "target_id": "p1", "lateral_speed_mps": 1.25},
        ],
    },
    "front_car_brake": {
        "name": "前车急停",
        "description": "前车快速制动，自车以较高速度持续逼近。",
        "weather": "rain",
        "ego_speed_kmh": 55,
        "duration_sec": 5,
        "targets": [
            {
                "id": "car1",
                "class_name": "car",
                "distance_m": 42,
                "lateral_m": 0.1,
                "longitudinal_speed_mps": 12,
            }
        ],
        "events": [
            {"time_sec": 1.5, "target_id": "car1", "longitudinal_acceleration_mps2": -7.5},
        ],
    },
    "motorcycle_cut_in": {
        "name": "两轮车并线",
        "description": "摩托车从右侧车道切入自车行驶路径。",
        "weather": "night",
        "ego_speed_kmh": 45,
        "duration_sec": 5,
        "aeb_safety_margin_m": 6,
        "targets": [
            {
                "id": "m1",
                "class_name": "motorcycle",
                "distance_m": 30,
                "lateral_m": 4.2,
                "lateral_speed_mps": 0,
                "longitudinal_speed_mps": 8.5,
            }
        ],
        "events": [
            {"time_sec": 1.0, "target_id": "m1", "lateral_speed_mps": -1.05},
            {"time_sec": 5.0, "target_id": "m1", "lateral_speed_mps": 0, "heading_rad": 0},
        ],
    },
    "red_light": {
        "name": "红灯路口",
        "description": "自车接近红灯停止线，检验信号灯约束风险。",
        "weather": "fog",
        "ego_speed_kmh": 30,
        "duration_sec": 4,
        "targets": [
            {
                "id": "light1",
                "class_name": "traffic light",
                "distance_m": 24,
                "lateral_m": 0,
                "state": "red",
            }
        ],
    },
    "mixed_intersection": {
        "name": "路口混流",
        "description": "路口同时出现前车、横穿行人和红灯，主风险目标会动态切换。",
        "weather": "rain",
        "ego_speed_kmh": 40,
        "duration_sec": 7,
        "targets": [
            {
                "id": "mix-car",
                "class_name": "car",
                "distance_m": 24,
                "lateral_m": 0.1,
                "longitudinal_speed_mps": 5,
            },
            {
                "id": "mix-person",
                "class_name": "person",
                "distance_m": 34,
                "lateral_m": -4.6,
                "lateral_speed_mps": 0,
            },
            {
                "id": "mix-light",
                "class_name": "traffic light",
                "distance_m": 31,
                "lateral_m": 0,
                "state": "red",
            },
        ],
        "events": [
            {"time_sec": 0.75, "target_id": "mix-car", "longitudinal_acceleration_mps2": -5.5},
            {"time_sec": 1.25, "target_id": "mix-person", "lateral_speed_mps": 1.35},
        ],
    },
}
