"""Validated REST CRUD endpoints scoped to each logged-in task owner."""
from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..models import Task
from .auth import login_required

tasks_bp = Blueprint("tasks", __name__)


def _json_object():
    if not request.is_json:
        return None
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _validate_task(data, *, partial=False):
    """Allow only custom fields, never a client-provided user_id."""
    if data is None:
        return None, "A JSON object is required"
    allowed = {"title", "description", "is_completed"}
    if not data or (set(data) - allowed):
        return None, "Provide at least one valid task field; user_id cannot be supplied"
    if not partial and "title" not in data:
        return None, "Title is required"

    cleaned = {}
    if "title" in data:
        title = data["title"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            return None, "Title must contain 1-120 characters"
        cleaned["title"] = title.strip()
    if "description" in data:
        description = data["description"]
        if not isinstance(description, str) or len(description) > 2000:
            return None, "Description must be a string of at most 2000 characters"
        cleaned["description"] = description
    if "is_completed" in data:
        is_completed = data["is_completed"]
        if not isinstance(is_completed, bool):
            return None, "is_completed must be a boolean"
        cleaned["is_completed"] = is_completed
    return cleaned, None


def _owned_task(task_id):
    """A record belonging to someone else is deliberately indistinguishable from 404."""
    return db.session.execute(
        db.select(Task).filter_by(id=task_id, user_id=g.current_user.id)
    ).scalar_one_or_none()


def _positive_query_int(name, default):
    raw = request.args.get(name)
    if raw is None:
        return default
    if not raw.isdecimal() or int(raw) < 1:
        return None
    return int(raw)


@tasks_bp.get("/tasks")
@login_required
def list_tasks():
    page = _positive_query_int("page", 1)
    per_page = _positive_query_int("per_page", 10)
    if page is None or per_page is None or per_page > 100:
        return jsonify({"error": "page and per_page must be positive (per_page <= 100)"}), 400

    statement = (
        db.select(Task)
        .filter_by(user_id=g.current_user.id)
        .order_by(Task.id.desc())
    )
    result = db.paginate(statement, page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [task.to_dict() for task in result.items],
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }), 200


@tasks_bp.post("/tasks")
@login_required
def create_task():
    values, error = _validate_task(_json_object())
    if error:
        return jsonify({"error": error}), 400
    task = Task(**values, user_id=g.current_user.id)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.get("/tasks/<int:task_id>")
@login_required
def get_task(task_id):
    task = _owned_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict()), 200


@tasks_bp.patch("/tasks/<int:task_id>")
@login_required
def update_task(task_id):
    task = _owned_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    values, error = _validate_task(_json_object(), partial=True)
    if error:
        return jsonify({"error": error}), 400
    for field, value in values.items():
        setattr(task, field, value)
    db.session.commit()
    return jsonify(task.to_dict()), 200


@tasks_bp.delete("/tasks/<int:task_id>")
@login_required
def delete_task(task_id):
    task = _owned_task(task_id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    db.session.delete(task)
    db.session.commit()
    return "", 204
