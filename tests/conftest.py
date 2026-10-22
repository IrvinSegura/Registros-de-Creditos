import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


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
