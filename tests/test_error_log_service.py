import unittest
from unittest.mock import patch

from backend.services.error_log_service import get_error_logs


class ErrorLogServiceTest(unittest.TestCase):
    def test_get_error_logs_collapses_same_second_duplicates(self):
        rows = [
            {
                "id": 2,
                "level": "WARN",
                "source": "flask_global",
                "error_type": "NotFound",
                "message": "请求的接口不存在：GET /api/missing",
                "request_path": "/api/missing",
                "request_method": "GET",
                "username": "liu",
                "status_code": 404,
                "created_at": "2026-07-14 11:03:06",
            },
            {
                "id": 1,
                "level": "WARN",
                "source": "flask_global",
                "error_type": "NotFound",
                "message": "请求的接口不存在：GET /api/missing",
                "request_path": "/api/missing",
                "request_method": "GET",
                "username": "liu",
                "status_code": 404,
                "created_at": "2026-07-14 11:03:06",
            },
        ]

        with patch("backend.services.error_log_service._db_list_error_logs", return_value=rows):
            logs = get_error_logs()

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["id"], 2)
        self.assertEqual(logs[0]["repeat_count"], 2)


if __name__ == "__main__":
    unittest.main()
