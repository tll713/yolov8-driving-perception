from flask import Blueprint, jsonify, request

from backend.api_contract import build_error_response, build_success_response
from backend.services.user_service import (
    UserServiceError,
    authenticate_any,
    authenticate_user,
    get_user_profile,
    register_user,
    update_user_profile,
)

auth_bp = Blueprint("auth", __name__)


def _service_error_response(error):
    return jsonify(build_error_response(str(error), error.code)), _status_from_code(error.code)


def _status_from_code(code):
    if code in {1004, 1005}:
        return 409
    if code in {1007, 1008, 1011, 1012}:
        return 401
    if code == 1010:
        return 404
    return 400


@auth_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        user = register_user(
            data.get("username"),
            data.get("email"),
            data.get("password"),
        )
    except UserServiceError as exc:
        return _service_error_response(exc)
    return jsonify(build_success_response(user, "注册成功"))


@auth_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    try:
        user = authenticate_any(data.get("username"), data.get("password"))
    except UserServiceError as exc:
        return _service_error_response(exc)
    return jsonify(build_success_response(user, "登录成功"))


@auth_bp.get("/auth/profile")
def profile():
    username = (request.args.get("username") or "").strip()
    try:
        user = get_user_profile(username)
    except UserServiceError as exc:
        return _service_error_response(exc)
    return jsonify(build_success_response(user))


@auth_bp.put("/auth/profile")
def update_profile():
    data = request.get_json(silent=True) or {}
    username = (data.get("current_username") or data.get("username") or "").strip()
    try:
        user = update_user_profile(username, data)
    except UserServiceError as exc:
        return _service_error_response(exc)
    return jsonify(build_success_response(user, "资料已更新"))
