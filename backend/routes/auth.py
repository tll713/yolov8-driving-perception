from flask import Blueprint, jsonify, request

from backend.api_contract import build_success_response, build_error_response

auth_bp = Blueprint("auth", __name__)

_users = []


@auth_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or len(username) < 3 or len(username) > 20:
        return jsonify(build_error_response("用户名需3-20个字符", 1001)), 400
    if not email or "@" not in email:
        return jsonify(build_error_response("请输入有效的邮箱地址", 1002)), 400
    if not password or len(password) < 6:
        return jsonify(build_error_response("密码至少6个字符", 1003)), 400
    if any(u["username"] == username for u in _users):
        return jsonify(build_error_response("用户名已存在", 1004)), 409
    if any(u["email"] == email for u in _users):
        return jsonify(build_error_response("邮箱已被注册", 1005)), 409

    _users.append({"username": username, "email": email, "password": password})
    return jsonify(build_success_response({"username": username}, "注册成功"))


@auth_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(build_error_response("用户名和密码不能为空", 1006)), 400

    user = next((u for u in _users if u["username"] == username), None)
    if not user or user["password"] != password:
        return jsonify(build_error_response("用户名或密码错误", 1007)), 401

    return jsonify(build_success_response({"username": username}, "登录成功"))