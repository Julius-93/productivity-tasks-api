"""Session authentication endpoints compatible with the supplied client."""
from functools import wraps

from flask import Blueprint, g, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User

auth_bp = Blueprint("auth", __name__)


def _json_object():
    """Reject invalid JSON rather than raising unexpected server errors."""
    if not request.is_json:
        return None
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _session_user():
    """Resolve signed-session user IDs against live database records."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = db.session.get(User, user_id)
    if user is None:
        session.clear()
    return user


def login_required(view):
    """Reject anonymous requests and expose the authenticated user on g."""
    @wraps(view)
    def decorated(*args, **kwargs):
        user = _session_user()
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        g.current_user = user
        return view(*args, **kwargs)

    return decorated


@auth_bp.post("/signup")
def signup():
    data = _json_object()
    if data is None:
        return jsonify({"error": "A JSON object is required"}), 400

    username = data.get("username")
    password = data.get("password")
    confirmation = data.get("password_confirmation")

    if not isinstance(username, str) or not 3 <= len(username.strip()) <= 50:
        return jsonify({"error": "Username must contain 3-50 characters"}), 400
    username = username.strip()
    if not isinstance(password, str) or not 8 <= len(password.encode("utf-8")) <= 72:
        return jsonify({"error": "Password must contain 8-72 UTF-8 bytes"}), 400
    if password != confirmation:
        return jsonify({"error": "Password confirmation does not match"}), 400
    if db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none():
        return jsonify({"error": "Username is already taken"}), 409

    user = User(username=username)
    user.password = password
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username is already taken"}), 409

    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    return jsonify(user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = _json_object()
    if data is None:
        return jsonify({"error": "A JSON object is required"}), 400
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Username and password are required"}), 400

    user = db.session.execute(
        db.select(User).filter_by(username=username.strip())
    ).scalar_one_or_none()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    return jsonify(user.to_dict()), 200


@auth_bp.get("/check_session")
def check_session():
    user = _session_user()
    if user is None:
        return jsonify({}), 401
    return jsonify(user.to_dict()), 200


@auth_bp.delete("/logout")
def logout():
    session.clear()
    return jsonify({}), 200
