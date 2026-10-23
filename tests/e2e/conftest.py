"""Browser tests: the real app served on a local port and driven with Playwright (pytest -m e2e).

They need the browser (python -m playwright install chromium) and internet access, because the pages
load Bootstrap, SweetAlert2 and Chart.js from a CDN.
"""

import socket
import threading
from decimal import Decimal

import pytest
from werkzeug.serving import make_server

from app import clock, create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Credit, CreditChange, Payment, User
from app.services import credit_service, user_service
from app.services.amortization import add_months

PASSWORD = "e2e-password-123"
# Accounts shared by every test; anything else a test creates is removed afterwards
BASE_USERS = {"admin": "Ana Admin", "analyst": "Luis Analista", "viewer": "Vera Consulta"}


def pytest_collection_modifyitems(items):
    for item in items:
        if "e2e" in item.path.parts:
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def live_app(tmp_path_factory):
    class E2EConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path_factory.mktemp('e2e') / 'credits.db'}"
        LOG_REQUESTS = False

    app = create_app(E2EConfig)
    with app.app_context():
        db.create_all()
        for role, full_name in BASE_USERS.items():
            user_service.create_user(role, full_name, PASSWORD, role)
    return app


@pytest.fixture(scope="session")
def base_url(live_app):
    """Overrides pytest-playwright's base_url, so pages are opened with relative paths."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = make_server("127.0.0.1", port, live_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture(autouse=True)
def clean_data(live_app):
    yield
    with live_app.app_context():
        for model in (Payment, CreditChange, Credit):
            db.session.execute(db.delete(model))
        db.session.execute(db.delete(User).where(User.username.not_in(BASE_USERS)))
        db.session.commit()


@pytest.fixture
def seed_credit(live_app):
    """Creates a credit straight in the database, as if someone else had registered it."""

    def _seed(client_name="Rosa Prueba", amount="12000", interest_rate="12", term_months=12, months_ago=0):
        with live_app.app_context():
            credit = credit_service.create_credit({
                "client_name": client_name,
                "amount": Decimal(amount),
                "interest_rate": Decimal(interest_rate),
                "term_months": term_months,
                "issue_date": add_months(clock.today(), -months_ago),
            })
            return credit.id

    return _seed


def sign_in(page, username, password=PASSWORD):
    page.goto("/login")
    page.locator("#username").fill(username)
    page.locator("#password").fill(password)
    page.get_by_role("button", name="Iniciar sesión").click()
    page.wait_for_url("**/#/panel")
