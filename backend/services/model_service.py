from pathlib import Path

from backend.config import DEFAULT_MODEL_PATH


_MODEL_CACHE = {}


def get_model(model_path=DEFAULT_MODEL_PATH):
    model_path = Path(model_path)
    cache_key = str(model_path.resolve())

    if cache_key not in _MODEL_CACHE:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("未安装 ultralytics，请先执行 pip install -r requirements.txt") from exc

        _MODEL_CACHE[cache_key] = YOLO(str(model_path))

    return _MODEL_CACHE[cache_key]


def clear_model_cache():
    _MODEL_CACHE.clear()
