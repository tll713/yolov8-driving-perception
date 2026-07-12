from pathlib import Path
from decimal import Decimal

from backend.config import BASE_DIR, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from risk import RISK_LABELS


RISK_ORDER = {"low": 1, "info": 2, "medium": 3, "high": 4}

USER_TABLE = "`用户表`"
RECORD_TABLE = "`检测记录表`"
OBJECT_TABLE = "`检测目标表`"
CATEGORY_TABLE = "`目标类别表`"
RISK_LOG_TABLE = "`风险日志表`"
RISK_RULE_TABLE = "`风险规则表`"


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


def _to_float(value, default=0):
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    return value


def _to_int(value, default=0):
    if value is None:
        return default
    return int(value)


def _risk_level(value):
    return value or "low"


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


def _get_user_id(cursor, username=None):
    if username:
        cursor.execute(
            f"SELECT `编号` AS id FROM {USER_TABLE} WHERE `用户名` = %s LIMIT 1",
            [username],
        )
        row = cursor.fetchone()
        if row:
            return row["id"]

    cursor.execute(
        f"""
        SELECT `编号` AS id
        FROM {USER_TABLE}
        WHERE `用户角色` = 'user'
        ORDER BY `编号` DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("用户表中没有可关联的用户，请先注册或登录用户")
    return row["id"]


def _get_category_id(cursor, class_name):
    class_name = class_name or "unknown"
    cursor.execute(
        f"SELECT `编号` AS id FROM {CATEGORY_TABLE} WHERE `英文类别名` = %s LIMIT 1",
        [class_name],
    )
    row = cursor.fetchone()
    if row:
        return row["id"]

    cursor.execute(
        f"""
        INSERT INTO {CATEGORY_TABLE} (
            `COCO类别编号`, `英文类别名`, `中文类别名`, `是否参与风险判断`, `风险类别`
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        [-1, class_name, RISK_LABELS.get(class_name, class_name), 1, "自动检测目标"],
    )
    return cursor.lastrowid


def _get_risk_rule_id(cursor, class_name, risk_level):
    cursor.execute(
        f"""
        SELECT `编号` AS id
        FROM {RISK_RULE_TABLE}
        WHERE `是否启用` = 1
          AND `风险等级` = %s
          AND (`适用类别` = %s OR `适用类别` LIKE %s)
        ORDER BY `编号`
        LIMIT 1
        """,
        [risk_level, class_name, f"%{class_name}%"],
    )
    row = cursor.fetchone()
    if row:
        return row["id"]

    cursor.execute(
        f"""
        INSERT INTO {RISK_RULE_TABLE} (
            `规则名称`, `适用类别`, `风险等级`, `判断条件`, `提示模板`, `是否启用`
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        [
            f"{class_name} {risk_level} 自动规则",
            class_name or "unknown",
            risk_level,
            "后端风险评估结果",
            "检测到风险目标",
            1,
        ],
    )
    return cursor.lastrowid


def save_detection_result(result):
    detections = result.get("detections", [])
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            user_id = _get_user_id(cursor, result.get("username"))
            cursor.execute(
                f"""
                INSERT INTO {RECORD_TABLE} (
                    `用户编号`, `原始文件名`, `文件类型`, `上传路径`, `结果路径`,
                    `模型名称`, `置信度阈值`, `图像宽度`, `图像高度`,
                    `目标总数`, `最高风险等级`, `推理耗时毫秒`
                ) VALUES (
                    %(user_id)s, %(original_filename)s, %(file_type)s,
                    %(upload_path)s, %(result_path)s, %(model_name)s,
                    %(confidence_threshold)s, %(image_width)s, %(image_height)s,
                    %(total_objects)s, %(max_risk_level)s, %(inference_time_ms)s
                )
                """,
                {
                    "user_id": user_id,
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
                    "inference_time_ms": int(result.get("inference_time_ms") or 0),
                },
            )
            record_id = cursor.lastrowid

            for detection in detections:
                payload = {
                    "record_id": record_id,
                    **_object_payload(detection, result.get("image_height", 0)),
                }
                payload["category_id"] = _get_category_id(cursor, payload["class_name"])
                cursor.execute(
                    f"""
                    INSERT INTO {OBJECT_TABLE} (
                        `检测记录编号`, `类别编号`, `置信度`,
                        `检测框左上角X`, `检测框左上角Y`,
                        `检测框右下角X`, `检测框右下角Y`,
                        `检测框面积`, `中心点X`, `中心点Y`
                    ) VALUES (
                        %(record_id)s, %(category_id)s, %(confidence)s,
                        %(bbox_x1)s, %(bbox_y1)s, %(bbox_x2)s, %(bbox_y2)s,
                        %(bbox_area)s, %(center_x)s, %(center_y)s
                    )
                    """,
                    payload,
                )
                object_id = cursor.lastrowid
                if payload["risk_level"] in {"medium", "high"}:
                    payload["risk_rule_id"] = _get_risk_rule_id(
                        cursor,
                        payload["class_name"],
                        payload["risk_level"],
                    )
                    cursor.execute(
                        f"""
                        INSERT INTO {RISK_LOG_TABLE} (
                            `检测记录编号`, `检测目标编号`, `风险规则编号`,
                            `风险等级`, `风险提示`, `风险原因`
                        ) VALUES (
                            %(record_id)s, %(object_id)s, %(risk_rule_id)s, %(risk_level)s,
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
                f"""
                SELECT
                    `编号` AS id,
                    `创建时间` AS created_at,
                    `原始文件名` AS original_filename,
                    `文件类型` AS file_type,
                    `上传路径` AS upload_path,
                    `结果路径` AS result_path,
                    `模型名称` AS model_name,
                    `置信度阈值` AS confidence_threshold,
                    `目标总数` AS total_objects,
                    `最高风险等级` AS max_risk_level,
                    `推理耗时毫秒` AS inference_time_ms
                FROM {RECORD_TABLE}
                ORDER BY `编号` DESC
                LIMIT %(limit)s
                """,
                {"limit": limit},
            )
            rows = cursor.fetchall()
            for row in rows:
                row["detections"] = _fetch_record_detections(cursor, row.get("id"))
    finally:
        conn.close()

    return [
        {
            "record_id": row.get("id"),
            "created_at": str(row.get("created_at") or ""),
            "type": row.get("file_type"),
            "filename": row.get("original_filename"),
            "upload_path": row.get("upload_path"),
            "result_path": row.get("result_path"),
            "model_name": row.get("model_name"),
            "confidence": _to_float(row.get("confidence_threshold")),
            "count": _to_int(row.get("total_objects")),
            "max_risk_level": row.get("max_risk_level"),
            "inference_time_ms": _to_int(row.get("inference_time_ms")),
            "detections": row.get("detections") or [],
        }
        for row in rows
    ]


def _record_payload(row, detections=None):
    return {
        "record_id": row.get("id"),
        "created_at": str(row.get("created_at") or ""),
        "type": row.get("file_type"),
        "filename": row.get("original_filename"),
        "upload_path": row.get("upload_path"),
        "result_path": row.get("result_path"),
        "model_name": row.get("model_name"),
        "confidence": _to_float(row.get("confidence_threshold")),
        "image_width": _to_int(row.get("image_width")),
        "image_height": _to_int(row.get("image_height")),
        "count": _to_int(row.get("total_objects")),
        "max_risk_level": row.get("max_risk_level"),
        "inference_time_ms": _to_int(row.get("inference_time_ms")),
        "detections": detections or [],
    }


def get_detection_result(record_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    `编号` AS id,
                    `创建时间` AS created_at,
                    `原始文件名` AS original_filename,
                    `文件类型` AS file_type,
                    `上传路径` AS upload_path,
                    `结果路径` AS result_path,
                    `模型名称` AS model_name,
                    `置信度阈值` AS confidence_threshold,
                    `图像宽度` AS image_width,
                    `图像高度` AS image_height,
                    `目标总数` AS total_objects,
                    `最高风险等级` AS max_risk_level,
                    `推理耗时毫秒` AS inference_time_ms
                FROM {RECORD_TABLE}
                WHERE `编号` = %(record_id)s
                """,
                {"record_id": record_id},
            )
            record = cursor.fetchone()
            if record is None:
                return None

            detections = _fetch_record_detections(cursor, record_id)
    finally:
        conn.close()

    return _record_payload(record, detections)


def _fetch_record_detections(cursor, record_id):
    cursor.execute(
        f"""
        SELECT
            o.`编号` AS id,
            c.`英文类别名` AS class_name,
            c.`中文类别名` AS class_name_cn,
            o.`置信度` AS confidence,
            o.`检测框左上角X` AS bbox_x1,
            o.`检测框左上角Y` AS bbox_y1,
            o.`检测框右下角X` AS bbox_x2,
            o.`检测框右下角Y` AS bbox_y2,
            o.`中心点X` AS center_x,
            o.`中心点Y` AS center_y,
            o.`检测框面积` AS bbox_area,
            r.`风险等级` AS risk_level,
            r.`风险提示` AS risk_message,
            r.`风险原因` AS risk_reason
        FROM {OBJECT_TABLE} o
        LEFT JOIN {CATEGORY_TABLE} c ON c.`编号` = o.`类别编号`
        LEFT JOIN {RISK_LOG_TABLE} r ON r.`检测目标编号` = o.`编号`
        WHERE o.`检测记录编号` = %(record_id)s
        ORDER BY o.`编号`
        """,
        {"record_id": record_id},
    )
    rows = cursor.fetchall()
    detections = [
        {
            "object_id": row.get("id"),
            "class_name": row.get("class_name"),
            "class_name_cn": row.get("class_name_cn"),
            "confidence": _to_float(row.get("confidence")),
            "bbox": [
                _to_int(row.get("bbox_x1")),
                _to_int(row.get("bbox_y1")),
                _to_int(row.get("bbox_x2")),
                _to_int(row.get("bbox_y2")),
            ],
            "bbox_area": _to_int(row.get("bbox_area")),
            "center_x": _to_int(row.get("center_x")),
            "center_y": _to_int(row.get("center_y")),
            "risk": {
                "level": _risk_level(row.get("risk_level")),
                "message": row.get("risk_message") or "",
                "reason": row.get("risk_reason") or "",
            },
        }
        for row in rows
    ]
    return detections
