"""Server-rendered pages and the health check."""

import logging

from flask import Blueprint, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

log = logging.getLogger(__name__)

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    return render_template("index.html")


@web_bp.get("/health")
def health():
    """For uptime monitors and load balancers: public, and 503 when the database does not answer."""
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.exception("Health check failed: the database does not answer")
        return {"status": "error", "database": "unavailable"}, 503
    return {"status": "ok", "database": "ok"}
