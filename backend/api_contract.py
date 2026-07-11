API_ENDPOINTS = {
    "health": "/api/health",
    "image_detection": "/api/detections/images",
    "video_detection": "/api/detections/videos",
    "video_detection_job_create": "/api/detections/videos/jobs",
    "video_detection_job_status": "/api/detections/videos/jobs/<job_id>",
    "history": "/api/detections/history",
    "history_clear": "/api/detections/history/clear",
    "detection_record": "/api/detections/records/<record_id>",
    "model_info": "/api/models/current",
    "simulation_presets": "/api/simulation/presets",
    "simulation_risk": "/api/simulation/risk",
    "simulation_scenarios": "/api/simulation/scenarios",
    "simulation_scenario_delete": "/api/simulation/scenarios/<scenario_id>",
}


def build_success_response(data=None, message="success"):
    return {
        "code": 0,
        "message": message,
        "data": data if data is not None else {},
    }


def build_error_response(message, code=400, data=None):
    return {
        "code": code,
        "message": message,
        "data": data,
    }
