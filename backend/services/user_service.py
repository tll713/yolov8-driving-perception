import json
from datetime import datetime
from threading import Lock
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from backend.config import USER_FILE


_LOCK = Lock()


class UserServiceError(ValueError):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def _now():
    return datetime.now().isoformat(timespec="seconds")


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
    username = (username or "").strip()
    data = _load_store()
    user = _find_by_username(data["users"], username)
    if not user:
        raise UserServiceError("用户不存在", 1010)
    return _public_user(user)


def update_user_profile(username, updates):
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
    data = _load_store()
    return [_public_user(user) for user in data["users"]]


def create_user_by_admin(username, email, password, status="active"):
    user = register_user(username, email, password)
    if status == "disabled":
        user = update_user_by_admin(user["username"], {"status": "disabled"})
    return user


def update_user_by_admin(username, updates):
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
    username = (username or "").strip()
    with _LOCK:
        data = _load_store()
        before = len(data["users"])
        data["users"] = [user for user in data["users"] if user.get("username") != username]
        if len(data["users"]) == before:
            raise UserServiceError("用户不存在", 1010)
        _save_store(data)


def register_admin(username, email, password):
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
    username = (username or "").strip()
    if not username or not password:
        raise UserServiceError("用户名和密码不能为空", 2005)

    data = _load_store()
    admin = _find_by_username(data["admins"], username)
    if not admin or not check_password_hash(admin.get("password_hash", ""), password):
        raise UserServiceError("管理员用户名或密码错误", 2006)
    return _public_user(admin)
