import logging
import sqlite3
from contextlib import closing

import pytest
from sqlalchemy.exc import OperationalError

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.logs import FORMAT, build_handler
from app.services import backup_service
from tests.conftest import sign_in


def test_each_request_is_logged_with_its_user(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.requests"):
        client.get("/api/v1/credits")

    line = next(record.getMessage() for record in caplog.records if record.name == "app.requests")
    assert line.startswith("GET /api/v1/credits 200 ")
    assert "user=admin" in line


def test_static_files_are_not_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.requests"):
        client.get("/static/css/base.css")

    assert not [record for record in caplog.records if record.name == "app.requests"]


def test_credit_changes_are_logged(client, create_credit, caplog):
    with caplog.at_level(logging.INFO, logger="app.services"):
        credit = create_credit()

    assert f"Credit {credit['id']} created by user" in caplog.text


def test_failed_sign_ins_are_logged_as_warnings(app, make_user, caplog):
    make_user(username="ana")
    with caplog.at_level(logging.WARNING):
        sign_in(app.test_client(), "ana", password="wrong-password")

    assert any(record.levelno == logging.WARNING and "ana" in record.getMessage() for record in caplog.records)


def test_health_check_is_public_and_not_logged(anonymous_client, caplog):
    with caplog.at_level(logging.INFO, logger="app.requests"):
        response = anonymous_client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}
    assert not [record for record in caplog.records if record.name == "app.requests"]


def test_health_check_reports_a_database_failure(anonymous_client, monkeypatch):
    def broken(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("database is locked"))

    monkeypatch.setattr(db.session, "execute", broken)

    response = anonymous_client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unavailable"}


def test_log_file_handler_rotates(tmp_path):
    handler = build_handler(str(tmp_path / "logs" / "app.log"))
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.emit(logging.makeLogRecord({"name": "app", "levelno": logging.INFO, "levelname": "INFO", "msg": "hola"}))
    handler.close()

    assert handler.maxBytes > 0 and handler.backupCount > 0
    assert "INFO    app: hola" in (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")


def test_unknown_log_level_is_rejected():
    class WrongLevel(TestingConfig):
        LOG_LEVEL = "LOUD"

    with pytest.raises(ValueError, match="LOG_LEVEL"):
        create_app(WrongLevel)


@pytest.fixture
def backups_in(app, tmp_path):
    app.config["BACKUP_DIR"] = str(tmp_path / "backups")
    return tmp_path / "backups"


def test_backup_copies_the_database(client, create_credit, backups_in):
    create_credit(client_name="Ana Paz")

    path = backup_service.create_backup()

    assert path.parent == backups_in
    # sqlite3's own context manager commits but does not close the connection
    with closing(sqlite3.connect(path)) as copy:
        assert copy.execute("SELECT client_name FROM credits").fetchall() == [("Ana Paz",)]


def test_backups_keep_only_the_newest_copies(app, backups_in):
    app.config["BACKUP_KEEP"] = 2

    paths = [backup_service.create_backup() for _ in range(3)]

    assert [backup.path for backup in backup_service.list_backups()] == paths[1:]


def test_backup_commands(app, backups_in):
    runner = app.test_cli_runner()

    created = runner.invoke(args=["backup", "create"])
    listed = runner.invoke(args=["backup", "list"])

    assert created.exit_code == 0, created.output
    assert "Respaldo guardado en" in created.output
    assert "credits-" in listed.output


def test_scheduled_backups_can_be_turned_off(app):
    app.config["BACKUP_INTERVAL_HOURS"] = 0

    assert backup_service.schedule_backups(app) is None
