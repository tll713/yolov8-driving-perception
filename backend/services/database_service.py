from pathlib import Path

from backend.config import BASE_DIR, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from risk import RISK_LABELS


RISK_ORDER = {"low": 1, "info": 2, "medium": 3, "high": 4}


def get_connection():
    import pymysql

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def _relative_path(value):
    if not value:
        return ""

    path = Path(value)
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _max_risk_level(detections):
    level = "low"
    for item in detections:
        current = item.get("risk", {}).get("level", "low")
        if RISK_ORDER.get(current, 0) > RISK_ORDER.get(level, 0):
            level = current
    return level


def _object_payload(detection, image_height):
    x1, y1, x2, y2 = detection.get("bbox", [0, 0, 0, 0])
    bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
    center_x = int((x1 + x2) / 2)
    center_y = int((y1 + y2) / 2)
    class_name = detection.get("class_name", "")
    risk = detection.get("risk", {})
    risk_reason = detection.get("risk_reason") or f"检测到 {class_name}"
    if center_y >= image_height * 0.5:
        risk_reason += "，且目标中心位于画面下半部分"

    return {
        "class_name": class_name,
        "class_name_cn": RISK_LABELS.get(class_name, class_name or "目标"),
        "confidence": detection.get("confidence", 0),
        "bbox_x1": x1,
        "bbox_y1": y1,
        "bbox_x2": x2,
        "bbox_y2": y2,
        "bbox_area": bbox_area,
        "center_x": center_x,
        "center_y": center_y,
        "risk_level": risk.get("level", "low"),
        "risk_message": risk.get("message", ""),
        "risk_reason": risk_reason,
    }


def save_detection_result(result):
    detections = result.get("detections", [])
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO detection_record (
                    original_filename, file_type, upload_path, result_path,
                    model_name, confidence_threshold, image_width, image_height,
                    total_objects, max_risk_level, inference_time_ms
                ) VALUES (
                    %(original_filename)s, %(file_type)s, %(upload_path)s, %(result_path)s,
                    %(model_name)s, %(confidence_threshold)s, %(image_width)s, %(image_height)s,
                    %(total_objects)s, %(max_risk_level)s, %(inference_time_ms)s
                )
                """,
                {
                    "original_filename": result.get("original_filename") or result.get("filename", ""),
                    "file_type": result.get("type", "image"),
                    "upload_path": _relative_path(result.get("upload_path", "")),
                    "result_path": _relative_path(result.get("result_path", "")),
                    "model_name": result.get("model_name", ""),
                    "confidence_threshold": result.get("confidence", 0),
                    "image_width": result.get("image_width", 0),
                    "image_height": result.get("image_height", 0),
                    "total_objects": len(detections),
                    "max_risk_level": _max_risk_level(detections),
                    "inference_time_ms": result.get("inference_time_ms", 0),
                },
            )
            record_id = cursor.lastrowid

            for detection in detections:
                payload = {
                    "record_id": record_id,
                    **_object_payload(detection, result.get("image_height", 0)),
                }
                cursor.execute(
                    """
                    INSERT INTO detected_object (
                        record_id, class_name, class_name_cn, confidence,
                        bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                        center_x, center_y, bbox_area,
                        risk_level, risk_message, risk_reason
                    ) VALUES (
                        %(record_id)s, %(class_name)s, %(class_name_cn)s, %(confidence)s,
                        %(bbox_x1)s, %(bbox_y1)s, %(bbox_x2)s, %(bbox_y2)s,
                        %(center_x)s, %(center_y)s, %(bbox_area)s,
                        %(risk_level)s, %(risk_message)s, %(risk_reason)s
                    )
                    """,
                    payload,
                )
                object_id = cursor.lastrowid
                if payload["risk_level"] in {"medium", "high"}:
                    cursor.execute(
                        """
                        INSERT INTO risk_log (
                            record_id, object_id, risk_level, risk_message, risk_reason
                        ) VALUES (
                            %(record_id)s, %(object_id)s, %(risk_level)s,
                            %(risk_message)s, %(risk_reason)s
                        )
                        """,
                        {**payload, "object_id": object_id},
                    )

        conn.commit()
        return record_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_detection_history(limit=50):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, original_filename, file_type, upload_path, result_path,
                    model_name, confidence_threshold, total_objects,
                    max_risk_level, inference_time_ms
                FROM detection_record
                ORDER BY id DESC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    return [
        {
            "record_id": row.get("id"),
            "type": row.get("file_type"),
            "filename": row.get("original_filename"),
            "upload_path": row.get("upload_path"),
            "result_path": row.get("result_path"),
            "model_name": row.get("model_name"),
            "confidence": row.get("confidence_threshold"),
            "count": row.get("total_objects"),
            "max_risk_level": row.get("max_risk_level"),
            "inference_time_ms": row.get("inference_time_ms"),
        }
        for row in rows
    ]


def _record_payload(row, detections=None):
    return {
        "record_id": row.get("id"),
        "type": row.get("file_type"),
        "filename": row.get("original_filename"),
        "upload_path": row.get("upload_path"),
        "result_path": row.get("result_path"),
        "model_name": row.get("model_name"),
        "confidence": row.get("confidence_threshold"),
        "image_width": row.get("image_width"),
        "image_height": row.get("image_height"),
        "count": row.get("total_objects"),
        "max_risk_level": row.get("max_risk_level"),
        "inference_time_ms": row.get("inference_time_ms"),
        "detections": detections or [],
    }


def get_detection_result(record_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, original_filename, file_type, upload_path, result_path,
                    model_name, confidence_threshold, image_width, image_height,
                    total_objects, max_risk_level, inference_time_ms
                FROM detection_record
                WHERE id = %(record_id)s
                """,
                {"record_id": record_id},
            )
            record = cursor.fetchone()
            if record is None:
                return None

            cursor.execute(
                """
                SELECT
                    id, class_name, class_name_cn, confidence,
                    bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                    center_x, center_y, bbox_area,
                    risk_level, risk_message, risk_reason
                FROM detected_object
                WHERE record_id = %(record_id)s
                ORDER BY id
                """,
                {"record_id": record_id},
            )
            rows = cursor.fetchall()
    finally:
        conn.close()

    detections = [
        {
            "object_id": row.get("id"),
            "class_name": row.get("class_name"),
            "class_name_cn": row.get("class_name_cn"),
            "confidence": row.get("confidence"),
            "bbox": [
                row.get("bbox_x1"),
                row.get("bbox_y1"),
                row.get("bbox_x2"),
                row.get("bbox_y2"),
            ],
            "bbox_area": row.get("bbox_area"),
            "center_x": row.get("center_x"),
            "center_y": row.get("center_y"),
            "risk": {
                "level": row.get("risk_level"),
                "message": row.get("risk_message"),
                "reason": row.get("risk_reason"),
            },
        }
        for row in rows
    ]
    return _record_payload(record, detections)
