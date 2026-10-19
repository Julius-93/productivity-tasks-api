"""Application factory: initialize configuration, database, and routes."""
from flask import Flask, jsonify

from config import Config
from .extensions import bcrypt, db, migrate


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    # Import models before migrations to make metadata discoverable.
    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    from .routes.tasks import tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)

    @app.get("/")
    def health():
        return jsonify({"message": "Productivity Tasks API is running"}), 200

    return app
