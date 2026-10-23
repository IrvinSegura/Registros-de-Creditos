"""Configuration classes selected through the APP_ENV environment variable."""

import os
from datetime import timedelta

DEFAULT_SECRET_KEY = "dev-only-change-me"


class BaseConfig:
    ENV_NAME = "base"
    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    # Relative SQLite paths resolve inside Flask's instance/ folder
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///credits.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False

    # Signed session cookie: unreadable from JavaScript, not sent on cross-site requests, valid for a work day
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Business time zone: decides what "today" is for dates, standings and due dates (see app/clock.py)
    TIMEZONE = os.getenv("APP_TIMEZONE", "America/Mexico_City")

    # Logs go to the console unless LOG_FILE names a file (relative paths land in instance/), see app/logs.py
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "")
    # One line per request; the development server already prints its own
    LOG_REQUESTS = True

    # Database copies made by `flask backup create` and by serve.py (see app/services/backup_service.py)
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
    BACKUP_KEEP = int(os.getenv("BACKUP_KEEP", "30"))
    BACKUP_INTERVAL_HOURS = float(os.getenv("BACKUP_INTERVAL_HOURS", "24"))

    # OpenAPI documentation served at /api/docs
    API_TITLE = "Credit Registry API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_JSON_PATH = "openapi.json"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/"


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True
    # `flask run` without --debug switches debug off, which would also keep edited templates cached
    TEMPLATES_AUTO_RELOAD = True
    LOG_REQUESTS = False


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"
    # Production is served over HTTPS only
    SESSION_COOKIE_SECURE = True


CONFIGS: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    name = name or os.getenv("APP_ENV", "development")
    try:
        return CONFIGS[name]
    except KeyError:
        raise ValueError(f"Unknown APP_ENV '{name}'. Expected one of: {', '.join(CONFIGS)}") from None
