"""Flask extensions, created unbound and initialized in the application factory."""

from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
# Batch mode lets Alembic alter tables on SQLite
migrate = Migrate(render_as_batch=True)
api = Api()
cors = CORS()
