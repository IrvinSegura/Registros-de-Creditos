"""Flask extensions, created unbound and initialized in the application factory."""

import sqlite3

from flask_login import LoginManager
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
# Batch mode lets Alembic alter tables on SQLite
migrate = Migrate(render_as_batch=True)
api = Api()
login_manager = LoginManager()


def _unicode_lower(value):
    return value.lower() if isinstance(value, str) else value


@event.listens_for(Engine, "connect")
def configure_sqlite(dbapi_connection, connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        # SQLite ignores foreign keys (and ON DELETE rules) unless each connection turns them on
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
        # SQLite's own lower() only handles A-Z, so "Á" or "Ñ" kept their case and searching
        # "ángel" missed "Ángel"; this one lowercases every letter, like PostgreSQL does
        dbapi_connection.create_function("lower", 1, _unicode_lower, deterministic=True)
