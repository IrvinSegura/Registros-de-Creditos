"""Application factory."""

from flask import Flask

from app import models  # noqa: F401  (registers the models with SQLAlchemy and Alembic)
from app.api.v1 import blueprints as api_v1_blueprints
from app.config import DEFAULT_SECRET_KEY, BaseConfig, get_config
from app.errors import register_error_handlers
from app.extensions import api, cors, db, migrate
from app.security import register_security_headers
from app.web import web_bp


def create_app(config_class: type[BaseConfig] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())
    _check_production_config(app)

    db.init_app(app)
    migrate.init_app(app, db)
    api.init_app(app)
    if app.config["CORS_ORIGINS"]:
        cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    for blueprint in api_v1_blueprints:
        api.register_blueprint(blueprint)
    app.register_blueprint(web_bp)
    register_error_handlers(app)
    register_security_headers(app)

    return app


def _check_production_config(app: Flask) -> None:
    if app.config["ENV_NAME"] == "production" and app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in production.")
