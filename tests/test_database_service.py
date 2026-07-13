import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.database_service import (
    get_detection_result,
    list_detection_history,
    save_detection_result,
)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.lastrowid = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.statements.append((sql, params))
        if "INSERT INTO `检测记录表`" in sql:
            self.lastrowid = 101
        elif "INSERT INTO `检测目标表`" in sql:
            self.lastrowid = 200 + self.connection.object_insert_count
            self.connection.object_insert_count += 1

    def fetchall(self):
        return [
            {
                "id": 101,
                "original_filename": "road_001.jpg",
                "file_type": "image",
                "upload_path": "uploads/road_001.jpg",
                "result_path": "",
                "model_name": "yolov8s",
                "confidence_threshold": 0.5,
                "total_objects": 1,
                "max_risk_level": "high",
                "inference_time_ms": 85,
            }
        ]

    def fetchone(self):
        return {
            "id": 101,
            "original_filename": "road_001.jpg",
            "file_type": "image",
            "upload_path": "uploads/road_001.jpg",
            "result_path": "",
            "model_name": "yolov8s",
            "confidence_threshold": 0.5,
            "image_width": 1280,
            "image_height": 720,
            "total_objects": 1,
            "max_risk_level": "high",
            "inference_time_ms": 85,
        }


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.object_insert_count = 1

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class DatabaseServiceTest(unittest.TestCase):
    def test_save_detection_result_inserts_record_objects_and_risk_logs(self):
        connection = FakeConnection()
        result = {
            "type": "image",
            "username": "liu",
            "original_filename": "road_001.jpg",
            "filename": "road_001.jpg",
            "upload_path": "uploads/road_001.jpg",
            "result_path": "",
            "model_name": "yolov8s",
            "confidence": 0.5,
            "image_width": 1280,
            "image_height": 720,
            "inference_time_ms": 85,
            "detections": [
                {
                    "class_name": "person",
                    "confidence": 0.8765,
                    "bbox": [520, 360, 650, 700],
                    "risk": {
                        "level": "high",
                        "message": "高风险：前方中央区域检测到行人",
                    },
                },
                {
                    "class_name": "traffic light",
                    "confidence": 0.77,
                    "bbox": [50, 60, 80, 120],
                    "risk": {
                        "level": "info",
                        "message": "前方检测到交通信号灯，请注意交通信息",
                    },
                },
            ],
        }

        with patch("backend.services.database_service.get_connection", return_value=connection):
            record_id = save_detection_result(result)

        self.assertEqual(record_id, 101)
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)
        sql_text = "\n".join(sql for sql, _ in connection.statements)
        self.assertIn("INSERT INTO `检测记录表`", sql_text)
        self.assertEqual(sql_text.count("INSERT INTO `检测目标表`"), 2)
        self.assertEqual(sql_text.count("INSERT INTO `风险日志表`"), 1)

        object_params = next(
            params
            for sql, params in connection.statements
            if "INSERT INTO `检测目标表`" in sql
        )
        self.assertEqual(object_params["class_name_cn"], "行人")
        self.assertEqual(object_params["bbox_area"], 44200)
        self.assertEqual(object_params["center_x"], 585)
        self.assertEqual(object_params["center_y"], 530)
        self.assertEqual(object_params["risk_reason"], "检测到 person，且目标中心位于画面下半部分")

    def test_save_detection_result_deduplicates_risk_logs_by_class_level_and_reason(self):
        connection = FakeConnection()
        result = {
            "type": "image",
            "username": "liu",
            "original_filename": "road_001.jpg",
            "filename": "road_001.jpg",
            "upload_path": "uploads/road_001.jpg",
            "result_path": "",
            "model_name": "yolov8s",
            "confidence": 0.5,
            "image_width": 1280,
            "image_height": 720,
            "inference_time_ms": 85,
            "detections": [
                {
                    "class_name": "car",
                    "confidence": 0.5,
                    "bbox": [520, 360, 650, 700],
                    "risk": {"level": "medium", "message": "中风险"},
                },
                {
                    "class_name": "car",
                    "confidence": 0.9,
                    "bbox": [530, 360, 660, 700],
                    "risk": {"level": "medium", "message": "中风险"},
                },
            ],
        }

        with patch("backend.services.database_service.get_connection", return_value=connection):
            save_detection_result(result)

        sql_text = "\n".join(sql for sql, _ in connection.statements)
        self.assertEqual(sql_text.count("INSERT INTO `风险日志表`"), 1)

    def test_list_detection_history_returns_recent_records(self):
        connection = FakeConnection()

        with patch("backend.services.database_service.get_connection", return_value=connection):
            items = list_detection_history(limit=5)

        self.assertEqual(items[0]["record_id"], 101)
        self.assertEqual(items[0]["filename"], "road_001.jpg")
        self.assertEqual(items[0]["count"], 1)
        self.assertTrue(connection.closed)

    def test_get_detection_result_returns_record_and_objects(self):
        connection = FakeConnection()
        object_rows = [
            {
                "id": 201,
                "class_name": "person",
                "class_name_cn": "行人",
                "confidence": 0.8765,
                "bbox_x1": 520,
                "bbox_y1": 360,
                "bbox_x2": 650,
                "bbox_y2": 700,
                "bbox_area": 44200,
                "center_x": 585,
                "center_y": 530,
                "risk_level": "high",
                "risk_message": "高风险：前方中央区域检测到行人",
                "risk_reason": "检测到 person，且目标中心位于画面下半部分",
            }
        ]

        with patch("backend.services.database_service.get_connection", return_value=connection):
            with patch.object(FakeCursor, "fetchall", return_value=object_rows):
                item = get_detection_result(101)

        self.assertEqual(item["record_id"], 101)
        self.assertEqual(item["filename"], "road_001.jpg")
        self.assertEqual(item["detections"][0]["bbox"], [520, 360, 650, 700])
        self.assertEqual(item["detections"][0]["risk"]["level"], "high")


if __name__ == "__main__":
    unittest.main()
