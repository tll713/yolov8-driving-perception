import unittest
from unittest.mock import patch

from backend.services.history_service import list_history


class HistoryServiceTest(unittest.TestCase):
    def test_list_history_uses_database_items_when_available(self):
        db_items = [{"record_id": 101, "filename": "road_001.jpg"}]

        with patch("backend.services.history_service.list_detection_history", return_value=db_items, create=True):
            self.assertEqual(list_history(), db_items)


if __name__ == "__main__":
    unittest.main()
