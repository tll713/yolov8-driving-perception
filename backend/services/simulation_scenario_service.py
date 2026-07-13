import json
from copy import deepcopy
from datetime import datetime
from threading import RLock
from uuid import uuid4

from backend.config import SIMULATION_SCENARIO_FILE
from backend.services.simulation_service import simulate_risk


_FILE_LOCK = RLock()
_SCENARIO_FIELDS = {
    "name",
    "description",
    "weather",
    "ego_speed_kmh",
    "duration_sec",
    "step_sec",
    "auto_brake",
    "brake_deceleration_mps2",
    "aeb_delay_sec",
    "aeb_ramp_sec",
    "aeb_safety_margin_m",
    "targets",
    "events",
}


def _read_items():
    if not SIMULATION_SCENARIO_FILE.exists():
        return []
    try:
        items = json.loads(SIMULATION_SCENARIO_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return items if isinstance(items, list) else []


def _write_items(items):
    SIMULATION_SCENARIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = SIMULATION_SCENARIO_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(SIMULATION_SCENARIO_FILE)


def list_custom_scenarios():
    with _FILE_LOCK:
        return deepcopy(_read_items())


def save_custom_scenario(payload):
    if not isinstance(payload, dict):
        raise ValueError("场景配置必须是对象")

    scenario = {key: deepcopy(value) for key, value in payload.items() if key in _SCENARIO_FIELDS}
    name = str(scenario.get("name", "")).strip()
    description = str(scenario.get("description", "")).strip()
    if not name:
        raise ValueError("场景名称不能为空")
    if len(name) > 80:
        raise ValueError("场景名称不能超过 80 个字符")
    if len(description) > 500:
        raise ValueError("场景描述不能超过 500 个字符")
    scenario["name"] = name
    scenario["description"] = description
    scenario.setdefault("weather", "clear")
    scenario.setdefault("ego_speed_kmh", 35)
    scenario.setdefault("duration_sec", 5)
    scenario.setdefault("step_sec", 0.25)
    scenario.setdefault("auto_brake", True)
    scenario.setdefault("targets", [])
    scenario.setdefault("events", [])

    scenario_id = str(payload.get("id") or uuid4().hex[:12])
    scenario["id"] = scenario_id
    scenario["key"] = f"custom:{scenario_id}"
    simulate_risk({**scenario, "scenario": scenario["key"]})

    now = datetime.now().isoformat(timespec="seconds")
    with _FILE_LOCK:
        items = _read_items()
        existing = next((item for item in items if item.get("id") == scenario_id), None)
        scenario["created_at"] = existing.get("created_at", now) if existing else now
        scenario["updated_at"] = now
        items = [item for item in items if item.get("id") != scenario_id]
        items.insert(0, scenario)
        _write_items(items[:100])
    return deepcopy(scenario)


def delete_custom_scenario(scenario_id):
    scenario_id = str(scenario_id)
    with _FILE_LOCK:
        items = _read_items()
        remaining = [item for item in items if item.get("id") != scenario_id]
        if len(remaining) == len(items):
            return False
        _write_items(remaining)
    return True
