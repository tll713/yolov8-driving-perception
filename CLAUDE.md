# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

Environment setup (Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the server:

```powershell
python app.py            # http://127.0.0.1:5000
```

Run the full test suite / a single test:

```powershell
python -m unittest discover -s tests
python -m unittest tests.test_detection_service
python -m unittest tests.test_detection_service.DetectionServiceTest.test_detect_uploaded_image_returns_backend_record_fields
```

Frontend static asset syntax check (no bundler in this project):

```powershell
node --check static\js\components.js
node --check static\js\app.js
```

Environment configuration lives in `.env` (see `.env.example`). Key vars: `FLASK_DEBUG`, MySQL `DB_*`, and YOLO tuning knobs (`YOLO_INFERENCE_MODE`, `YOLO_IMAGE_SIZE`, `YOLO_REFINE_*`, `YOLO_DEVICE`).

## Architecture

Two-layer Flask app: a thin routing layer under `backend/routes/` and business logic under `backend/services/`. Detection primitives (`detect.py`, `risk.py`, `utils.py`) sit at the repo root and are imported by services. `app.py` at the root is only a launcher; the real Flask factory is `backend.create_app` (see `backend/app.py`).

### Request flow — image detection

`POST /api/detections/images` → `backend/routes/detections.py:detect_image_endpoint`
→ `detection_service.detect_uploaded_image`
→ `utils.save_upload` (writes to `uploads/` with a uuid filename)
→ `detect.detect_image` (YOLOv8 predict + optional two-pass refine)
→ `risk.assess_detections` (per-box scoring, lane-overlap, distance heuristics)
→ `result_renderer.render_detection_image` (writes annotated image to `results/`)
→ `demo_analysis_service` builds `scene_summary`, `decision_trace`, `demo_script`, `safety_advice`
→ `database_service.save_detection_result` (MySQL; failure is swallowed, `database_saved=False`)
→ `history_service.append_history` (JSON fallback at `logs/detection_history.json`)

### Video detection

Two entry points:

- **Synchronous:** `POST /api/detections/videos` runs `detect_video_file` inline.
- **Async job:** `POST /api/detections/videos/jobs` spawns a daemon thread in `video_job_service`, then poll `GET /api/detections/videos/jobs/<job_id>`. Progress frames are written to `results/<job>_frame_<idx>.jpg` and a per-frame `detection_timeline` accumulates in the in-memory `_JOBS` dict guarded by `_LOCK`.

Both paths reuse `detect_video_file` in `detection_service.py`; the job service passes a `progress_callback` for streaming updates.

### Two-tier persistence

`history_service.list_history` first tries `database_service.list_detection_history` (MySQL via PyMySQL) and silently falls back to the JSON file at `logs/detection_history.json` if the DB is unreachable. This means routes should not assume MySQL is up. `_save_to_database` in `detection_service.py` also wraps insertion in a try/except and sets `database_saved` on the result rather than failing the request.

### Model lifecycle

`backend/services/model_service.py` holds a process-wide `_MODEL_CACHE` keyed by resolved path. `warmup_model()` is called during `create_app()` so the first inference request doesn't pay the load cost. If `models/yolov8s.pt` is missing, `get_model` raises `RuntimeError` — the model file is gitignored and must be provided manually.

### Risk scoring

`risk.py` is the single source of truth for per-detection risk **on real detections**. It computes a "driving corridor" trapezoid (`_driving_corridor_bounds`) and combines lane overlap, bottom-y distance proxy, class-based risk weight, and confidence into a 0–100 score, then maps to `low` / `info` / `medium` / `high`. `traffic light` and `stop sign` always map to `info` regardless of score. `summarize_risk` aggregates counts and max level for the response envelope.

### Simulation sandbox

`backend/services/simulation_service.py` (routes in `backend/routes/simulation.py`, endpoints `GET /api/simulation/presets` and `POST /api/simulation/risk`) is a **separate** risk pipeline that does not touch YOLO or `risk.py`. It takes a scenario config (ego speed, target list with class/distance/lateral offset/speed, weather key) and produces a per-frame timeline with TTC, lane overlap, per-target risk score, and a `perception_fps` degraded by `WEATHER_PROFILES[*].fps_factor`. Uses include tuning the class-weight/TTC thresholds without running inference, driving the frontend 3D risk-simulation view, and generating demo timelines from `PRESET_SCENARIOS` (normal cruise, pedestrian crossing, front-car brake, motorcycle cut-in, red light). Keep its scoring bands (`_risk_level`) roughly aligned with `risk.py`'s bands, but do not assume the two share code — they don't.

### API response envelope

Every JSON response uses `{code, message, data}` built via `backend/api_contract.py:build_success_response` / `build_error_response`. Endpoints are enumerated in `API_ENDPOINTS` in the same file (health, models, detections image/video/jobs/history/records, simulation presets/risk) — keep this list in sync when adding routes. Frontend (`static/js/app.js`) reads that map from `/api`.

### Frontend

Vue 3 loaded from `static/js/vue.global.prod.js` (no build step). Pages are separate Jinja templates in `templates/` (`index.html`, `history.html`, `preview.html`, `risk_analysis.html`, admin pages), each mounting components defined in `static/js/components.js` with orchestration in `static/js/app.js`.

## Working conventions (from AGENTS.md)

- Keep route handlers thin: validation + response envelope only; put logic in services.
- Preserve existing result field names — `type`, `original_filename`, `confidence`, `detections`, `risk`, `max_risk_level`, `risk_counts`, `scene_summary`, `decision_trace`, `demo_script`, `safety_advice`. Tests and frontend both depend on these.
- Prefer reusing existing services over inlining new logic into routes.
- MySQL config comes from env vars — don't hardcode credentials.
- When changing API behavior, update `backend/api_contract.py` and relevant tests together.

## Runtime directories

`uploads/`, `results/`, `logs/`, `models/` are created on startup by `ensure_runtime_directories()`. Contents are gitignored (`.gitkeep` preserves the empty dirs). `results/` is served at `/results/<filename>` via `send_from_directory`.
