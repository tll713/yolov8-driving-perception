from copy import deepcopy
from threading import Lock, Thread
import traceback
from uuid import uuid4

from backend.config import ALLOWED_VIDEO_EXTENSIONS, DEFAULT_CONFIDENCE, RESULT_DIR, UPLOAD_DIR
from backend.services.error_log_service import log_error
from backend.services.detection_service import (
    _validate_confidence,
    _validate_file,
    detect_video_file,
)
from utils import save_upload


_JOBS = {}
_LOCK = Lock()


def _job_snapshot(job_id):
    with _LOCK:
        job = _JOBS.get(job_id)
        return deepcopy(job) if job else None


def get_video_detection_job(job_id):
    return _job_snapshot(job_id)


def start_video_detection_job(upload, confidence=DEFAULT_CONFIDENCE, username=None):
    _validate_file(upload, ALLOWED_VIDEO_EXTENSIONS, "视频")
    confidence = _validate_confidence(confidence)
    original_filename = upload.filename
    upload_path = save_upload(upload, upload_dir=UPLOAD_DIR)
    job_id = uuid4().hex

    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "original_filename": original_filename,
            "latest_frame": None,
            "detection_timeline": [],
            "detections": [],
            "result": None,
            "error": "",
        }

    thread = Thread(
        target=_run_video_detection_job,
        args=(job_id, upload_path, original_filename, confidence, username),
        daemon=True,
    )
    thread.start()
    return _job_snapshot(job_id)


def _run_video_detection_job(job_id, upload_path, original_filename, confidence, username=None):
    import cv2

    def publish_progress(payload):
        frame = payload.pop("frame")
        frame_index = payload["frame_index"]
        frame_filename = f"{job_id}_frame_{frame_index}.jpg"
        RESULT_DIR.mkdir(exist_ok=True)
        cv2.imwrite(str(RESULT_DIR / frame_filename), frame)
        timeline_item = {
            "frame_index": frame_index,
            "timestamp_sec": payload["timestamp_sec"],
            "image_width": payload["image_width"],
            "image_height": payload["image_height"],
            "detections": payload["detections"],
            "lane_analysis": payload.get("lane_analysis"),
            "max_risk_level": payload.get("frame_max_risk_level", "low"),
            "max_risk_score": payload.get("frame_max_risk_score", 0),
            "risk_counts": payload.get("frame_risk_counts", {}),
            "inference_time_ms": payload.get("frame_inference_time_ms", 0),
            "average_inference_time_ms": payload.get("average_frame_inference_time_ms", 0),
        }

        with _LOCK:
            job = _JOBS[job_id]
            timeline = job.setdefault("detection_timeline", [])
            if not timeline or timeline[-1]["frame_index"] != frame_index:
                timeline.append(timeline_item)
            job.update(
                {
                    "status": "running",
                    "progress": payload["progress"],
                    "latest_frame": {
                        "frame_index": frame_index,
                        "timestamp_sec": payload["timestamp_sec"],
                        "image_width": payload["image_width"],
                        "image_height": payload["image_height"],
                        "image_url": f"/results/{frame_filename}",
                        "result_filename": frame_filename,
                        "detections": payload["detections"],
                        "lane_analysis": payload.get("lane_analysis"),
                        "max_risk_level": payload.get("frame_max_risk_level", "low"),
                        "max_risk_score": payload.get("frame_max_risk_score", 0),
                        "risk_counts": payload.get("frame_risk_counts", {}),
                        "inference_time_ms": payload.get("frame_inference_time_ms", 0),
                        "average_inference_time_ms": payload.get("average_frame_inference_time_ms", 0),
                    },
                    "lane_analysis": payload.get("lane_analysis"),
                    "detections": payload["all_detections"],
                    "count": len(payload["all_detections"]),
                    "max_risk_level": payload.get("max_risk_level", "low"),
                    "max_risk_score": payload.get("max_risk_score", 0),
                    "risk_counts": payload.get("risk_counts", {}),
                    "scene_summary": payload.get("scene_summary"),
                    "decision_trace": payload.get("decision_trace", []),
                    "demo_script": payload.get("demo_script", []),
                    "safety_advice": payload.get("safety_advice", []),
                }
            )

    with _LOCK:
        _JOBS[job_id]["status"] = "running"

    try:
        result = detect_video_file(
            upload_path,
            original_filename,
            confidence=confidence,
            progress_callback=publish_progress,
            username=username,
        )
    except Exception as exc:
        log_error(
            level="ERROR",
            source="video_detection_job",
            error_type=type(exc).__name__,
            message=f"{original_filename}: {exc}",
            username=(username or "").strip(),
            status_code=500,
            stack_trace=traceback.format_exc(),
        )
        with _LOCK:
            _JOBS[job_id].update({"status": "failed", "progress": 100, "error": str(exc)})
        return

    with _LOCK:
        result["detection_timeline"] = list(_JOBS[job_id].get("detection_timeline", []))
        _JOBS[job_id].update(
            {
                "status": "completed",
                "progress": 100,
                "result": result,
                "detections": result.get("detections", []),
                "count": result.get("count", 0),
                "max_risk_level": result.get("max_risk_level", "low"),
                "max_risk_score": result.get("max_risk_score", 0),
                "risk_counts": result.get("risk_counts", {}),
                "scene_summary": result.get("scene_summary"),
                "decision_trace": result.get("decision_trace", []),
                "demo_script": result.get("demo_script", []),
                "safety_advice": result.get("safety_advice", []),
                "lane_analysis": result.get("lane_analysis"),
            }
        )
