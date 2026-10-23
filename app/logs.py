"""Application logs: one format for the app, Waitress and Flask, plus one line per request."""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from flask import Flask, Response, g, request
from flask.logging import default_handler
from flask_login import current_user

FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
HANDLER_NAME = "app"
# A rotated log file never grows past MAX_BYTES; the oldest of BACKUP_COUNT copies is dropped
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5

request_log = logging.getLogger("app.requests")
# Static files and the health check, which a monitor may call every few seconds, would only add noise
QUIET_ENDPOINTS = frozenset({"static", "web.health"})


def check_log_level(name: str) -> None:
    if name.upper() not in logging.getLevelNamesMapping():
        raise ValueError(f"Unknown LOG_LEVEL '{name}'. Use DEBUG, INFO, WARNING or ERROR.")


def configure_logging(app: Flask) -> None:
    # Messages reach the root handler below; Flask's own handler would print them a second time
    app.logger.removeHandler(default_handler)
    # Tests read the records through pytest instead of a handler
    if not app.testing:
        log_file = app.config["LOG_FILE"]
        if log_file:
            # Relative paths land in instance/, next to the SQLite database
            log_file = os.path.join(app.instance_path, log_file)
        install_handler(app.config["LOG_LEVEL"], log_file)

    if app.config["LOG_REQUESTS"]:
        _log_requests(app)


def build_handler(log_file: str) -> logging.Handler:
    if not log_file:
        return logging.StreamHandler()
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    return RotatingFileHandler(log_file, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")


def install_handler(level: str, log_file: str) -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    # create_app can run more than once in a process (CLI commands, tests); keep a single handler
    if any(handler.get_name() == HANDLER_NAME for handler in root.handlers):
        return
    handler = build_handler(log_file)
    handler.set_name(HANDLER_NAME)
    handler.setFormatter(logging.Formatter(FORMAT))
    root.addHandler(handler)


def _log_requests(app: Flask) -> None:
    @app.before_request
    def start_timer() -> None:
        g.request_started = time.perf_counter()

    @app.after_request
    def log_request(response: Response) -> Response:
        if request.endpoint in QUIET_ENDPOINTS:
            return response
        elapsed_ms = (time.perf_counter() - g.get("request_started", time.perf_counter())) * 1000
        user = current_user.username if current_user.is_authenticated else "-"
        request_log.info(
            "%s %s %s %.0fms user=%s ip=%s",
            request.method, request.path, response.status_code, elapsed_ms, user, request.remote_addr,
        )
        return response
