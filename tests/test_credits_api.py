from datetime import date, timedelta

import pytest

URL = "/api/v1/credits"


def test_create_credit_returns_the_resource(client, valid_credit):
    response = client.post(URL, json=valid_credit)

    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 1
    assert body["client_name"] == "María López"
    assert body["amount"] == "15000.50"
    assert body["interest_rate"] == "12.75"
    assert body["issue_date"] == "2026-10-01"
    assert body["created_at"]


def test_create_credit_normalizes_client_name_spaces(create_credit):
    assert create_credit(client_name="  Ana    Paz ")["client_name"] == "Ana Paz"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("client_name", "ana"),
        ("client_name", "<script>alert(1)</script>"),
        ("client_name", "Jo"),
        ("amount", 0),
        ("amount", "abc"),
        ("amount", "10.005"),
        ("interest_rate", 0),
        ("interest_rate", "10.555"),
        ("interest_rate", 100.01),
        ("term_months", 0),
        ("term_months", 361),
        ("term_months", "12"),
        ("issue_date", "1999-12-31"),
        ("issue_date", "31/12/2026"),
        ("issue_date", (date.today() + timedelta(days=1)).isoformat()),
    ],
)
def test_create_credit_rejects_invalid_data(client, valid_credit, field, value):
    response = client.post(URL, json={**valid_credit, field: value})

    assert response.status_code == 422
    assert field in response.get_json()["errors"]["json"]


def test_create_credit_explains_each_rule(client, valid_credit):
    too_large = client.post(URL, json={**valid_credit, "amount": "1000000000000"}).get_json()["errors"]["json"]
    extra_places = client.post(URL, json={**valid_credit, "amount": "10.005"}).get_json()["errors"]["json"]
    future = client.post(URL, json={**valid_credit, "issue_date": "2999-01-01"}).get_json()["errors"]["json"]

    assert too_large["amount"] == ["El monto debe ser mayor a 0 y como máximo 999,999,999,999.99."]
    assert extra_places["amount"] == ["Usa como máximo 2 decimales."]
    assert future["issue_date"] == ["La fecha no puede ser posterior a hoy."]


def test_create_credit_accepts_trailing_zeros_and_today(create_credit):
    created = create_credit(amount="1500.500", interest_rate="9.50", issue_date=date.today().isoformat())

    assert created["amount"] == "1500.50"
    assert created["interest_rate"] == "9.50"


def test_create_credit_requires_every_field(client):
    response = client.post(URL, json={})

    assert response.status_code == 422
    errors = response.get_json()["errors"]["json"]
    assert set(errors) == {"client_name", "amount", "interest_rate", "term_months", "issue_date"}
    assert errors["client_name"] == ["Este campo es obligatorio."]


def test_create_credit_rejects_read_only_fields(client, valid_credit):
    response = client.post(URL, json={**valid_credit, "id": 99})

    assert response.status_code == 422
    assert "id" in response.get_json()["errors"]["json"]


def test_list_credits_is_paginated(client, create_credit):
    for name in ["Ana Paz", "Bruno Diaz", "Carla Ruiz"]:
        create_credit(client_name=name)

    body = client.get(f"{URL}?page=2&per_page=2").get_json()

    assert [c["client_name"] for c in body["items"]] == ["Carla Ruiz"]
    assert body["meta"] == {"page": 2, "per_page": 2, "total": 3, "pages": 2}


def test_list_credits_filters_by_client_name(client, create_credit):
    create_credit(client_name="Ana Paz")
    create_credit(client_name="Bruno Diaz")

    body = client.get(f"{URL}?client_name=paz").get_json()

    assert [c["client_name"] for c in body["items"]] == ["Ana Paz"]
    assert body["meta"]["total"] == 1


def test_list_credits_rejects_invalid_pagination(client):
    assert client.get(f"{URL}?per_page=101").status_code == 422
    assert client.get(f"{URL}?page=0").status_code == 422


def test_get_credit(client, create_credit):
    created = create_credit()

    response = client.get(f"{URL}/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == created


def test_update_credit(client, create_credit, valid_credit):
    created = create_credit()

    response = client.put(f"{URL}/{created['id']}", json={**valid_credit, "term_months": 36, "amount": "20000"})

    assert response.status_code == 200
    assert response.get_json()["term_months"] == 36
    assert client.get(f"{URL}/{created['id']}").get_json()["amount"] == "20000.00"


def test_update_credit_validates_data(client, create_credit, valid_credit):
    created = create_credit()

    response = client.put(f"{URL}/{created['id']}", json={**valid_credit, "term_months": -1})

    assert response.status_code == 422


def test_delete_credit(client, create_credit):
    created = create_credit()

    response = client.delete(f"{URL}/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"{URL}/{created['id']}").status_code == 404


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_credit_returns_404(client, valid_credit, method):
    response = getattr(client, method)(f"{URL}/999", json=valid_credit)

    assert response.status_code == 404
    assert response.get_json() == {"code": 404, "status": "Not Found", "message": "Crédito 999 no encontrado."}


def test_home_page_and_api_docs(client):
    assert client.get("/").status_code == 200
    assert client.get("/api/docs").status_code == 200
    spec = client.get("/api/openapi.json").get_json()
    assert "/api/v1/credits" in spec["paths"]


def test_summary_of_an_empty_portfolio(client):
    body = client.get(f"{URL}/summary").get_json()

    assert body["total_credits"] == 0
    assert body["total_amount"] == "0.00"
    assert body["average_term_months"] == "0.0"
    assert body["monthly"] == []
    assert [r["credits"] for r in body["by_term"]] == [0, 0, 0, 0]


def test_summary_aggregates_the_portfolio(client, create_credit):
    create_credit(amount=1000, interest_rate=10, term_months=12, issue_date="2026-01-10")
    create_credit(amount=2000.5, interest_rate=20, term_months=24, issue_date="2026-01-20")
    create_credit(amount=3000, interest_rate=15, term_months=48, issue_date="2026-03-05")

    body = client.get(f"{URL}/summary").get_json()

    assert body["total_credits"] == 3
    assert body["total_amount"] == "6000.50"
    assert body["average_amount"] == "2000.17"
    assert body["average_interest_rate"] == "15.00"
    assert body["average_term_months"] == "28.0"
    assert body["monthly"] == [
        {"year": 2026, "month": 1, "credits": 2, "total_amount": "3000.50"},
        {"year": 2026, "month": 3, "credits": 1, "total_amount": "3000.00"},
    ]
    assert body["by_term"] == [
        {"range": "1-12", "credits": 1},
        {"range": "13-24", "credits": 1},
        {"range": "25-36", "credits": 0},
        {"range": "37+", "credits": 1},
    ]
