import csv
import io

import pytest

URL = "/api/v1/credits"


@pytest.fixture
def portfolio(create_credit):
    create_credit(client_name="Ana Paz", amount=1000, interest_rate=10, term_months=12, issue_date="2026-01-10")
    create_credit(client_name="Bruno Diaz", amount=5000, interest_rate=20, term_months=24, issue_date="2026-02-20")
    create_credit(client_name="Carla Ruiz", amount=3000, interest_rate=15, term_months=48, issue_date="2026-03-05")
    create_credit(client_name="Ana Paz", amount=2500, interest_rate=12, term_months=6, issue_date="2026-03-15")


def names(response):
    return [c["client_name"] for c in response.get_json()["items"]]


def test_quote_estimates_the_monthly_payment(client):
    body = client.get(f"{URL}/quote?amount=10000&interest_rate=12&term_months=12").get_json()

    assert body == {"monthly_payment": "888.49", "total_interest": "661.86", "total_paid": "10661.86"}


def test_quote_validates_its_arguments(client):
    response = client.get(f"{URL}/quote?amount=0&interest_rate=12")

    assert response.status_code == 422
    assert set(response.get_json()["errors"]["query"]) == {"amount", "term_months"}


def test_amortization_schedule_of_a_credit(client, create_credit):
    credit = create_credit(amount=10000, interest_rate=12, term_months=12, issue_date="2026-01-15")

    body = client.get(f"{URL}/{credit['id']}/amortization").get_json()

    assert body["monthly_payment"] == "888.49"
    assert len(body["installments"]) == 12
    assert body["installments"][0] == {
        "number": 1,
        "due_date": "2026-02-15",
        "payment": "888.49",
        "interest": "100.00",
        "principal": "788.49",
        "balance": "9211.51",
    }
    assert body["installments"][-1]["balance"] == "0.00"


def test_list_sorts_by_any_column(client, portfolio):
    assert names(client.get(f"{URL}?sort=amount&order=desc")) == ["Bruno Diaz", "Carla Ruiz", "Ana Paz", "Ana Paz"]
    assert names(client.get(f"{URL}?sort=issue_date&order=asc"))[0] == "Ana Paz"
    assert client.get(f"{URL}?sort=password").status_code == 422


def test_list_filters_by_date_and_amount(client, portfolio):
    response = client.get(f"{URL}?issue_date_from=2026-02-01&issue_date_to=2026-03-10&amount_min=2000")

    assert names(response) == ["Bruno Diaz", "Carla Ruiz"]


def test_list_rejects_inverted_ranges(client):
    response = client.get(f"{URL}?issue_date_from=2026-05-01&issue_date_to=2026-01-01&amount_min=9&amount_max=1")

    assert response.status_code == 422
    assert set(response.get_json()["errors"]["query"]) == {"issue_date_to", "amount_max"}


def test_export_returns_the_filtered_credits_as_csv(client, portfolio):
    response = client.get(f"{URL}/export?client_name=ana&sort=amount&order=desc")

    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    text = response.get_data(as_text=True)
    assert text.startswith("﻿")
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    assert rows[0] == ["ID", "Cliente", "Monto", "Tasa anual (%)", "Plazo (meses)", "Fecha de otorgamiento"]
    assert [row[2] for row in rows[1:]] == ["2500.00", "1000.00"]


def test_history_records_creation_and_real_changes_only(client, create_credit, valid_credit):
    credit = create_credit()
    url = f"{URL}/{credit['id']}"

    client.put(url, json={**valid_credit, "term_months": 36, "amount": "20000"})
    client.put(url, json={**valid_credit, "term_months": 36, "amount": "20000"})

    history = client.get(f"{url}/history").get_json()
    assert [entry["action"] for entry in history] == ["updated", "created"]
    assert history[0]["changes"] == {
        "amount": {"old": "15000.50", "new": "20000.00"},
        "term_months": {"old": 24, "new": 36},
    }
    assert history[1]["changes"]["client_name"] == {"old": None, "new": "María López"}


def test_history_is_deleted_with_its_credit(client, create_credit):
    from app.extensions import db
    from app.models import CreditChange

    credit = create_credit()
    client.delete(f"{URL}/{credit['id']}")

    assert client.get(f"{URL}/{credit['id']}/history").status_code == 404
    assert db.session.scalar(db.select(db.func.count(CreditChange.id))) == 0


def test_summary_can_be_limited_to_a_period(client, portfolio):
    body = client.get(f"{URL}/summary?issue_date_from=2026-03-01&issue_date_to=2026-03-31").get_json()

    assert body["total_credits"] == 2
    assert body["total_amount"] == "5500.00"
    assert [m["month"] for m in body["monthly"]] == [3]


def test_summary_ranks_the_top_clients(client, portfolio):
    top = client.get(f"{URL}/summary").get_json()["top_clients"]

    assert top[0] == {"client_name": "Bruno Diaz", "credits": 1, "total_amount": "5000.00"}
    assert top[1] == {"client_name": "Ana Paz", "credits": 2, "total_amount": "3500.00"}
