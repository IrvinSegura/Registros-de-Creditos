import pytest

from app import clock, create_app
from app.config import ProductionConfig, TestingConfig, get_config


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "dev-only-change-me")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(ProductionConfig)


def test_unknown_app_env_is_rejected():
    with pytest.raises(ValueError, match="APP_ENV"):
        get_config("staging")


def test_unknown_time_zone_is_rejected(monkeypatch):
    monkeypatch.setattr(TestingConfig, "TIMEZONE", "Mars/Olympus")

    with pytest.raises(ValueError, match="APP_TIMEZONE"):
        create_app(TestingConfig)


def test_today_follows_the_configured_time_zone(app):
    # UTC+14 is always at least one calendar day ahead of UTC-11
    app.config["TIMEZONE"] = "Pacific/Kiritimati"
    ahead = clock.today()
    app.config["TIMEZONE"] = "Pacific/Pago_Pago"
    behind = clock.today()

    assert ahead > behind
