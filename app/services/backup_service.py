"""Copies of the SQLite database, made with SQLite's online backup so the app keeps running meanwhile."""

import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from flask import Flask, current_app

from app import clock
from app.errors import DomainError
from app.extensions import db

log = logging.getLogger(__name__)

# credits-20261022-213000.db: names sort by date, newest last
PREFIX = "credits-"
SUFFIX = ".db"
STAMP_FORMAT = "%Y%m%d-%H%M%S"


class BackupError(DomainError):
    pass


@dataclass(frozen=True)
class Backup:
    path: Path
    size: int
    created_at: datetime


def backup_dir() -> Path:
    # Relative folders land in instance/, next to the database
    return Path(current_app.instance_path, current_app.config["BACKUP_DIR"])


def create_backup() -> Path:
    if db.engine.dialect.name != "sqlite":
        # The message is read by whoever runs the command, so it stays in Spanish
        raise BackupError("Los respaldos integrados solo funcionan con SQLite; usa las herramientas de tu base de datos.")

    folder = backup_dir()
    folder.mkdir(parents=True, exist_ok=True)
    target = _free_name(folder, clock.now().strftime(STAMP_FORMAT))
    with db.engine.connect() as connection:
        destination = sqlite3.connect(target)
        try:
            # Consistent copy even while other requests write to the database
            connection.connection.driver_connection.backup(destination)
        finally:
            destination.close()

    removed = prune(current_app.config["BACKUP_KEEP"])
    log.info("Database backup written to %s (%d old copies removed)", target, removed)
    return target


def list_backups() -> list[Backup]:
    folder = backup_dir()
    if not folder.is_dir():
        return []
    files = sorted(folder.glob(f"{PREFIX}*{SUFFIX}"), key=_order)
    return [
        Backup(path=path, size=path.stat().st_size, created_at=datetime.fromtimestamp(path.stat().st_mtime))
        for path in files
    ]


def prune(keep: int) -> int:
    """Deletes all but the newest `keep` copies; returns how many were deleted."""
    old = list_backups()[:-keep] if keep > 0 else []
    for backup in old:
        backup.path.unlink()
    return len(old)


def schedule_backups(app: Flask) -> threading.Thread | None:
    """Copies the database now and then every BACKUP_INTERVAL_HOURS, in a background thread."""
    hours = app.config["BACKUP_INTERVAL_HOURS"]
    if hours <= 0:
        log.info("Scheduled database backups are off (BACKUP_INTERVAL_HOURS=0)")
        return None

    def run() -> None:
        while True:
            with app.app_context():
                try:
                    create_backup()
                except BackupError as error:
                    log.warning("Scheduled backups stopped: %s", error.message)
                    return
                except Exception:
                    # A failed copy (full disk, locked folder) must not stop the next ones
                    log.exception("Database backup failed")
            threading.Event().wait(hours * 3600)

    thread = threading.Thread(target=run, name="database-backups", daemon=True)
    thread.start()
    log.info("Database backups every %s hours in %s", hours, Path(app.instance_path, app.config["BACKUP_DIR"]))
    return thread


def _order(path: Path) -> tuple[str, int]:
    # credits-<date>-<time>[-<n>].db: oldest first, and the -n copies after the first one of that second
    parts = path.name[len(PREFIX):-len(SUFFIX)].split("-")
    number = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    return "-".join(parts[:2]), number


def _free_name(folder: Path, stamp: str) -> Path:
    # Two copies within the same second get -2, -3... instead of overwriting each other
    target = folder / f"{PREFIX}{stamp}{SUFFIX}"
    number = 2
    while target.exists():
        target = folder / f"{PREFIX}{stamp}-{number}{SUFFIX}"
        number += 1
    return target
