import unittest
from unittest.mock import patch

from backend.services import user_service


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 1
        self.lastrowid = 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.statements.append((sql, params))

    def fetchone(self):
        return None

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class UserServiceMysqlTest(unittest.TestCase):
    def test_register_user_writes_to_configured_chinese_user_table(self):
        connection = FakeConnection()

        with patch.object(user_service, "USER_STORAGE", "mysql"):
            with patch("backend.services.user_service.get_connection", return_value=connection):
                user = user_service.register_user("test123", "test123@example.com", "secret123")

        self.assertEqual(user["username"], "test123")
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

        sql_text = "\n".join(sql for sql, _ in connection.statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `用户表`", sql_text)
        self.assertIn("INSERT INTO `用户表`", sql_text)
        self.assertIn("`用户名`", sql_text)
        self.assertIn("`邮箱`", sql_text)
        self.assertIn("`密码哈希`", sql_text)
        self.assertNotIn("system_user", sql_text)


if __name__ == "__main__":
    unittest.main()
