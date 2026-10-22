import pytest

from app import create_app
from app.config import ProductionConfig, get_config


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "dev-only-change-me")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(ProductionConfig)


def test_unknown_app_env_is_rejected():
    with pytest.raises(ValueError, match="APP_ENV"):
        get_config("staging")
