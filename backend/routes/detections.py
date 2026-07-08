from flask import Blueprint, jsonify, request

from backend.api_contract import build_error_response, build_success_response
from backend.config import DEFAULT_CONFIDENCE
from backend.services.database_service import get_detection_result
from backend.services.detection_service import detect_uploaded_image, detect_uploaded_video
from backend.services.history_service import list_history


detections_bp = Blueprint("detections", __name__)


@detections_bp.post("/detections/images")
def detect_image_endpoint():
    upload = request.files.get("file")
    if upload is None:
        return jsonify(build_error_response("请上传图片文件", 400)), 400

    try:
        confidence = float(request.form.get("confidence", DEFAULT_CONFIDENCE))
        result = detect_uploaded_image(upload, confidence=confidence)
    except ValueError as exc:
        return jsonify(build_error_response(str(exc), 400)), 400
    except RuntimeError as exc:
        return jsonify(build_error_response(str(exc), 503)), 503
    except Exception as exc:
        return jsonify(build_error_response(f"检测失败：{exc}", 500)), 500

    return jsonify(build_success_response(result))


@detections_bp.post("/detections/videos")
def detect_video_endpoint():
    upload = request.files.get("file")
    if upload is None:
        return jsonify(build_error_response("请上传视频文件", 400)), 400

    try:
        confidence = float(request.form.get("confidence", DEFAULT_CONFIDENCE))
        result = detect_uploaded_video(upload, confidence=confidence)
    except ValueError as exc:
        return jsonify(build_error_response(str(exc), 400)), 400
    except RuntimeError as exc:
        return jsonify(build_error_response(str(exc), 503)), 503
    except Exception as exc:
        return jsonify(build_error_response(f"检测失败：{exc}", 500)), 500

    return jsonify(build_success_response(result))


@detections_bp.get("/detections/history")
def detection_history():
    return jsonify(build_success_response({"items": list_history()}))


@detections_bp.get("/detections/records/<int:record_id>")
def detection_record(record_id):
    try:
        result = get_detection_result(record_id)
    except Exception as exc:
        return jsonify(build_error_response(f"查询检测结果失败：{exc}", 500)), 500

    if result is None:
        return jsonify(build_error_response("检测记录不存在", 404)), 404

    return jsonify(build_success_response(result))
