API_ENDPOINTS = {
    "health": "/api/health",
    "image_detection": "/api/detections/images",
    "video_detection": "/api/detections/videos",
    "history": "/api/detections/history",
    "model_info": "/api/models/current",
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
