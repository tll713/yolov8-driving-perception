import json
from datetime import datetime
from threading import Lock
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import USER_FILE, USER_STORAGE
from backend.services.database_service import get_connection


_LOCK = Lock()
_USER_TABLE = "system_user"


class UserServiceError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _use_mysql():
    return USER_STORAGE == "mysql"


def _mysql_error(error):
    return UserServiceError(f"用户数据库操作失败：{error}", 3001)


def _empty_store():
    return {"users": [], "admins": []}


def _load_store():
    if not USER_FILE.exists():
        return _empty_store()
    try:
        data = json.loads(USER_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_store()
    return {
        "users": list(data.get("users") or []),
        "admins": list(data.get("admins") or []),
    }


def _save_store(data):
    USER_FILE.parent.mkdir(exist_ok=True)
    USER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _ensure_user_table(conn):
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_USER_TABLE} (
                id VARCHAR(32) PRIMARY KEY,
                username VARCHAR(20) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE KEY uk_system_user_email_role (email, role),
                KEY idx_system_user_role (role),
                KEY idx_system_user_status (status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )


def _db_public_user(row):
    if not row:
        return None
    return {
        "id": row.get("id"),
        "username": row.get("username"),
        "email": row.get("email", ""),
        "role": row.get("role", "user"),
        "status": row.get("status", "active"),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
    }


def _db_find_by_username(conn, username, role=None):
    sql = f"SELECT * FROM {_USER_TABLE} WHERE username = %s"
    params = [username]
    if role is not None:
        sql += " AND role = %s"
        params.append(role)
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _db_find_by_email(conn, email, role, exclude_id=None):
    sql = f"SELECT * FROM {_USER_TABLE} WHERE email = %s AND role = %s"
    params = [email, role]
    if exclude_id is not None:
        sql += " AND id <> %s"
        params.append(exclude_id)
    with conn.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _db_create_account(username, email, password, role, status="active"):
    username = _validate_username(username)
    email = _validate_email(email)
    password = _validate_password(password)
    if status not in {"active", "disabled"}:
        raise UserServiceError("用户状态不合法", 1013)

    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        if _db_find_by_username(conn, username):
            message = "管理员用户名已存在" if role == "admin" else "用户名已存在"
            code = 2004 if role == "admin" else 1004
            raise UserServiceError(message, code)
        if _db_find_by_email(conn, email, role):
            raise UserServiceError("邮箱已被注册", 1005)

        user = {
            "id": uuid4().hex,
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": role,
            "status": status,
            "created_at": _now(),
            "updated_at": _now(),
        }
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO {_USER_TABLE} (
                    id, username, email, password_hash, role, status, created_at, updated_at
                ) VALUES (
                    %(id)s, %(username)s, %(email)s, %(password_hash)s,
                    %(role)s, %(status)s, %(created_at)s, %(updated_at)s
                )
                """,
                user,
            )
        conn.commit()
        return _public_user(user)
    except UserServiceError:
        conn.rollback()
        raise
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _db_authenticate_account(username, password, role):
    username = (username or "").strip()
    if not username or not password:
        code = 2005 if role == "admin" else 1006
        raise UserServiceError("用户名和密码不能为空", code)

    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        user = _db_find_by_username(conn, username, role)
        if not user or not check_password_hash(user.get("password_hash", ""), password):
            message = "管理员用户名或密码错误" if role == "admin" else "用户名或密码错误"
            code = 2006 if role == "admin" else 1007
            raise UserServiceError(message, code)
        if user.get("status") == "disabled":
            raise UserServiceError("该用户已被管理员禁用", 1008)
        return _db_public_user(user)
    except UserServiceError:
        raise
    except Exception as exc:
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _db_get_user_profile(username):
    username = (username or "").strip()
    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        user = _db_find_by_username(conn, username, "user")
        if not user:
            raise UserServiceError("用户不存在", 1010)
        return _db_public_user(user)
    except UserServiceError:
        raise
    except Exception as exc:
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _db_update_user_profile(username, updates):
    username = (username or "").strip()
    new_username = (updates.get("new_username") or updates.get("username") or username).strip()
    email = updates.get("email")
    old_password = updates.get("old_password") or ""
    new_password = updates.get("new_password") or ""

    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        user = _db_find_by_username(conn, username, "user")
        if not user:
            raise UserServiceError("用户不存在", 1010)

        fields = {}
        if new_username != username:
            new_username = _validate_username(new_username)
            existing = _db_find_by_username(conn, new_username)
            if existing and existing.get("id") != user.get("id"):
                raise UserServiceError("用户名已存在", 1004)
            fields["username"] = new_username

        if email is not None:
            email = _validate_email(email)
            if _db_find_by_email(conn, email, "user", exclude_id=user.get("id")):
                raise UserServiceError("邮箱已被注册", 1005)
            fields["email"] = email

        if new_password:
            _validate_password(new_password)
            if not old_password:
                raise UserServiceError("修改密码需要输入当前密码", 1011)
            if not check_password_hash(user.get("password_hash", ""), old_password):
                raise UserServiceError("当前密码错误", 1012)
            fields["password_hash"] = generate_password_hash(new_password)

        fields["updated_at"] = _now()
        assignments = ", ".join([f"{key} = %({key})s" for key in fields])
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE {_USER_TABLE} SET {assignments} WHERE id = %(id)s",
                {**fields, "id": user["id"]},
            )
        conn.commit()
        return _db_get_user_profile(fields.get("username", username))
    except UserServiceError:
        conn.rollback()
        raise
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _db_list_users():
    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, username, email, role, status, created_at, updated_at
                FROM {_USER_TABLE}
                WHERE role = 'user'
                ORDER BY created_at DESC
                """
            )
            return [_db_public_user(row) for row in cursor.fetchall()]
    except Exception as exc:
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _db_update_user_by_admin(username, updates):
    username = (username or "").strip()
    new_username = updates.get("username")
    email = updates.get("email")
    password = updates.get("password") or ""
    status = updates.get("status")

    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        user = _db_find_by_username(conn, username, "user")
        if not user:
            raise UserServiceError("用户不存在", 1010)

        fields = {}
        if new_username is not None and new_username.strip() != username:
            new_username = _validate_username(new_username)
            existing = _db_find_by_username(conn, new_username)
            if existing and existing.get("id") != user.get("id"):
                raise UserServiceError("用户名已存在", 1004)
            fields["username"] = new_username

        if email is not None:
            email = _validate_email(email)
            if _db_find_by_email(conn, email, "user", exclude_id=user.get("id")):
                raise UserServiceError("邮箱已被注册", 1005)
            fields["email"] = email

        if password:
            fields["password_hash"] = generate_password_hash(_validate_password(password))

        if status is not None:
            if status not in {"active", "disabled"}:
                raise UserServiceError("用户状态不合法", 1013)
            fields["status"] = status

        if not fields:
            return _db_public_user(user)

        fields["updated_at"] = _now()
        assignments = ", ".join([f"{key} = %({key})s" for key in fields])
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE {_USER_TABLE} SET {assignments} WHERE id = %(id)s",
                {**fields, "id": user["id"]},
            )
        conn.commit()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {_USER_TABLE} WHERE id = %s", [user["id"]])
            return _db_public_user(cursor.fetchone())
    except UserServiceError:
        conn.rollback()
        raise
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _db_delete_user_by_admin(username):
    username = (username or "").strip()
    conn = None
    try:
        conn = get_connection()
        _ensure_user_table(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {_USER_TABLE} WHERE username = %s AND role = 'user'",
                [username],
            )
            if cursor.rowcount == 0:
                raise UserServiceError("用户不存在", 1010)
        conn.commit()
    except UserServiceError:
        conn.rollback()
        raise
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise _mysql_error(exc) from exc
    finally:
        if conn is not None:
            conn.close()


def _validate_username(username):
    username = (username or "").strip()
    if len(username) < 3 or len(username) > 20:
        raise UserServiceError("用户名需3-20个字符", 1001)
    return username


def _validate_email(email):
    email = (email or "").strip()
    if not email or "@" not in email:
        raise UserServiceError("请输入有效的邮箱地址", 1002)
    return email


def _validate_password(password):
    if not password or len(password) < 6:
        raise UserServiceError("密码至少6个字符", 1003)
    return password


def _public_user(user):
    if not user:
        return None
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email", ""),
        "role": user.get("role", "user"),
        "status": user.get("status", "active"),
        "created_at": user.get("created_at", ""),
        "updated_at": user.get("updated_at", ""),
    }


def _find_by_username(items, username):
    return next((item for item in items if item.get("username") == username), None)


def _find_by_email(items, email, exclude_username=None):
    return next(
        (
            item
            for item in items
            if item.get("email") == email and item.get("username") != exclude_username
        ),
        None,
    )


def register_user(username, email, password):
    if _use_mysql():
        return _db_create_account(username, email, password, "user")

    username = _validate_username(username)
    email = _validate_email(email)
    password = _validate_password(password)

    with _LOCK:
        data = _load_store()
        if _find_by_username(data["users"], username):
            raise UserServiceError("用户名已存在", 1004)
        if _find_by_email(data["users"], email):
            raise UserServiceError("邮箱已被注册", 1005)

        user = {
            "id": uuid4().hex,
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": "user",
            "status": "active",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data["users"].append(user)
        _save_store(data)
        return _public_user(user)


def authenticate_user(username, password):
    if _use_mysql():
        return _db_authenticate_account(username, password, "user")

    username = (username or "").strip()
    if not username or not password:
        raise UserServiceError("用户名和密码不能为空", 1006)

    data = _load_store()
    user = _find_by_username(data["users"], username)
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        raise UserServiceError("用户名或密码错误", 1007)
    if user.get("status") == "disabled":
        raise UserServiceError("该用户已被管理员禁用", 1008)
    return _public_user(user)


def get_user_profile(username):
    if _use_mysql():
        return _db_get_user_profile(username)

    username = (username or "").strip()
    data = _load_store()
    user = _find_by_username(data["users"], username)
    if not user:
        raise UserServiceError("用户不存在", 1010)
    return _public_user(user)


def update_user_profile(username, updates):
    if _use_mysql():
        return _db_update_user_profile(username, updates)

    username = (username or "").strip()
    new_username = (updates.get("new_username") or updates.get("username") or username).strip()
    email = updates.get("email")
    old_password = updates.get("old_password") or ""
    new_password = updates.get("new_password") or ""

    with _LOCK:
        data = _load_store()
        user = _find_by_username(data["users"], username)
        if not user:
            raise UserServiceError("用户不存在", 1010)

        if new_username != username:
            new_username = _validate_username(new_username)
            if _find_by_username(data["users"], new_username):
                raise UserServiceError("用户名已存在", 1004)
            user["username"] = new_username

        if email is not None:
            email = _validate_email(email)
            if _find_by_email(data["users"], email, exclude_username=user["username"]):
                raise UserServiceError("邮箱已被注册", 1005)
            user["email"] = email

        if new_password:
            _validate_password(new_password)
            if not old_password:
                raise UserServiceError("修改密码需要输入当前密码", 1011)
            if not check_password_hash(user.get("password_hash", ""), old_password):
                raise UserServiceError("当前密码错误", 1012)
            user["password_hash"] = generate_password_hash(new_password)

        user["updated_at"] = _now()
        _save_store(data)
        return _public_user(user)


def list_users():
    if _use_mysql():
        return _db_list_users()

    data = _load_store()
    return [_public_user(user) for user in data["users"]]


def create_user_by_admin(username, email, password, status="active"):
    user = register_user(username, email, password)
    if status == "disabled":
        user = update_user_by_admin(user["username"], {"status": "disabled"})
    return user


def update_user_by_admin(username, updates):
    if _use_mysql():
        return _db_update_user_by_admin(username, updates)

    username = (username or "").strip()
    new_username = updates.get("username")
    email = updates.get("email")
    password = updates.get("password") or ""
    status = updates.get("status")

    with _LOCK:
        data = _load_store()
        user = _find_by_username(data["users"], username)
        if not user:
            raise UserServiceError("用户不存在", 1010)

        if new_username is not None and new_username.strip() != username:
            new_username = _validate_username(new_username)
            if _find_by_username(data["users"], new_username):
                raise UserServiceError("用户名已存在", 1004)
            user["username"] = new_username

        if email is not None:
            email = _validate_email(email)
            if _find_by_email(data["users"], email, exclude_username=user["username"]):
                raise UserServiceError("邮箱已被注册", 1005)
            user["email"] = email

        if password:
            user["password_hash"] = generate_password_hash(_validate_password(password))

        if status is not None:
            if status not in {"active", "disabled"}:
                raise UserServiceError("用户状态不合法", 1013)
            user["status"] = status

        user["updated_at"] = _now()
        _save_store(data)
        return _public_user(user)


def delete_user_by_admin(username):
    if _use_mysql():
        return _db_delete_user_by_admin(username)

    username = (username or "").strip()
    with _LOCK:
        data = _load_store()
        before = len(data["users"])
        data["users"] = [user for user in data["users"] if user.get("username") != username]
        if len(data["users"]) == before:
            raise UserServiceError("用户不存在", 1010)
        _save_store(data)


def register_admin(username, email, password):
    if _use_mysql():
        return _db_create_account(username, email, password, "admin")

    username = _validate_username(username)
    email = _validate_email(email)
    password = _validate_password(password)

    with _LOCK:
        data = _load_store()
        if _find_by_username(data["admins"], username):
            raise UserServiceError("管理员用户名已存在", 2004)

        admin = {
            "id": uuid4().hex,
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "role": "admin",
            "status": "active",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data["admins"].append(admin)
        _save_store(data)
        return _public_user(admin)


def authenticate_admin(username, password):
    if _use_mysql():
        return _db_authenticate_account(username, password, "admin")

    username = (username or "").strip()
    if not username or not password:
        raise UserServiceError("用户名和密码不能为空", 2005)

    data = _load_store()
    admin = _find_by_username(data["admins"], username)
    if not admin or not check_password_hash(admin.get("password_hash", ""), password):
        raise UserServiceError("管理员用户名或密码错误", 2006)
    return _public_user(admin)
