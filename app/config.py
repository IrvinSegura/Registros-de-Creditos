"""Configuration classes selected through the APP_ENV environment variable."""

import os
from datetime import timedelta

DEFAULT_SECRET_KEY = "dev-only-change-me"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


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

    # Cross-origin access is disabled unless origins are listed explicitly
    CORS_ORIGINS = _split_csv(os.getenv("CORS_ORIGINS", ""))

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
