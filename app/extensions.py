"""Flask extensions, created unbound and initialized in the application factory."""

import sqlite3

from flask_cors import CORS
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
cors = CORS()
login_manager = LoginManager()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    # SQLite ignores foreign keys (and ON DELETE rules) unless each connection turns them on
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
