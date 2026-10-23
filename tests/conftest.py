from functools import partial

import pytest
from flask import g
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.services import user_service

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def fast_password_hashing(monkeypatch):
    # scrypt is slow on purpose; tests only need a valid hash
    monkeypatch.setattr(user_service, "generate_password_hash", partial(generate_password_hash, method="pbkdf2:sha256:1000"))


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    # The app context below stays open for the whole test, so requests share `g`; without this,
    # the user Flask-Login caches there would leak from one request (or client) into the next
    def forget_cached_user():
        g.pop("_login_user", None)

    app.before_request_funcs.setdefault(None, []).insert(0, forget_cached_user)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def make_user(app):
    def _make(username="admin", role="admin", full_name="Ana Admin", password=PASSWORD):
        return user_service.create_user(username, full_name, password, role)

    return _make


def sign_in(client, username, password=PASSWORD):
    """Signs in through the real form and makes later requests send the CSRF token, like the frontend."""
    client.get("/login")
    with client.session_transaction() as session:
        token = session["csrf_token"]
    response = client.post("/login", data={"username": username, "password": password, "csrf_token": token})
    with client.session_transaction() as session:
        client.environ_base["HTTP_X_CSRF_TOKEN"] = session.get("csrf_token", "")
    return response


@pytest.fixture
def anonymous_client(app):
    return app.test_client()


@pytest.fixture
def client_as(app, make_user):
    """A client signed in with the given role."""

    def _client(role, username=None):
        username = username or role
        make_user(username=username, role=role, full_name=f"Usuario {role.capitalize()}")
        client = app.test_client()
        assert sign_in(client, username).status_code == 302
        return client

    return _client


@pytest.fixture
def client(client_as):
    return client_as("admin")


@pytest.fixture
def valid_credit():
    return {
        "client_name": "María López",
        "amount": 15000.5,
        "interest_rate": 12.75,
        "term_months": 24,
        "issue_date": "2026-10-01",
    }


@pytest.fixture
def create_credit(client, valid_credit):
    def _create(**changes):
        response = client.post("/api/v1/credits", json={**valid_credit, **changes})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _create
