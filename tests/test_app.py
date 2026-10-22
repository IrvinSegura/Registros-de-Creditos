import pytest

from app import create_app
from config import Config

URL = "/creditos"
VALID_CREDIT = {
    "cliente": "Maria Lopez",
    "monto": 1000,
    "tasa_interes": 12.5,
    "plazo": 12,
    "fecha_otorgamiento": "2026-10-22",
}


class InMemoryConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


@pytest.fixture
def client():
    return create_app(InMemoryConfig).test_client()


def test_home_page(client):
    assert client.get("/").status_code == 200


def test_create_and_list_credit(client):
    assert client.post(URL, json=VALID_CREDIT).status_code == 201

    credits = client.get(URL).get_json()

    assert len(credits) == 1
    assert credits[0]["cliente"] == "Maria Lopez"
    assert credits[0]["fecha_otorgamiento"] == "2026-10-22"


def test_create_credit_runs_schema_validators(client):
    response = client.post(URL, json={**VALID_CREDIT, "cliente": "Ana", "monto": -1})

    assert response.status_code == 400
    assert set(response.get_json()) == {"cliente", "monto"}


def test_update_and_delete_credit(client):
    client.post(URL, json=VALID_CREDIT)

    assert client.put(f"{URL}/1", json={**VALID_CREDIT, "plazo": 24}).status_code == 200
    assert client.get(f"{URL}/1").get_json()["plazo"] == 24
    assert client.delete(f"{URL}/1").status_code == 200
    assert client.get(f"{URL}/1").status_code == 404


def test_missing_credit_returns_404(client):
    assert client.get(f"{URL}/99").status_code == 404
    assert client.put(f"{URL}/99", json=VALID_CREDIT).status_code == 404
    assert client.delete(f"{URL}/99").status_code == 404
