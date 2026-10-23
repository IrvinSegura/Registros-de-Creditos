from datetime import timedelta

import pytest

from app import clock
from app.services.amortization import add_months

URL = "/api/v1/credits"


@pytest.fixture
def credit(create_credit):
    # Two installments of 888.49 already past due, the third one still ahead
    issued = add_months(clock.today(), -2) - timedelta(days=1)
    return create_credit(amount=10000, interest_rate=12, term_months=12, issue_date=issued.isoformat())


def pay(client, credit_id, amount, paid_on=None, note=""):
    return client.post(
        f"{URL}/{credit_id}/payments",
        json={"amount": amount, "paid_on": (paid_on or clock.today()).isoformat(), "note": note},
    )


def test_unpaid_installments_make_a_credit_overdue(client, credit):
    standing = client.get(f"{URL}/{credit['id']}").get_json()["standing"]

    assert standing["status"] == "overdue"
    assert standing["overdue_installments"] == 2
    assert standing["overdue_amount"] == "1776.98"
    assert standing["days_overdue"] > 30


def test_recording_payments_updates_the_standing(client, credit):
    response = pay(client, credit["id"], "1776.98", note="  Transferencia   123 ")

    assert response.status_code == 201
    payment = response.get_json()
    assert (payment["amount"], payment["note"], payment["recorded_by"]) == ("1776.98", "Transferencia 123", "Usuario Admin")
    standing = client.get(f"{URL}/{credit['id']}").get_json()["standing"]
    assert standing["status"] == "active"
    assert standing["installments_paid"] == 2
    assert standing["overdue_amount"] == "0.00"


def test_payments_are_listed_newest_first(client, credit):
    pay(client, credit["id"], "100", paid_on=clock.today() - timedelta(days=3))
    pay(client, credit["id"], "200")

    payments = client.get(f"{URL}/{credit['id']}/payments").get_json()

    assert [payment["amount"] for payment in payments] == ["200.00", "100.00"]


@pytest.mark.parametrize(
    ("amount", "days", "field", "message"),
    [
        ("0", 0, "amount", "El monto debe ser mayor a 0"),
        ("10.005", 0, "amount", "Usa como máximo 2 decimales."),
        ("100", -1, "paid_on", "La fecha no puede ser posterior a hoy."),
        ("100", 400, "paid_on", "no puede ser anterior al otorgamiento"),
        ("999999", 0, "amount", "El pago supera lo que falta por pagar"),
    ],
)
def test_payments_are_validated(client, credit, amount, days, field, message):
    response = pay(client, credit["id"], amount, paid_on=clock.today() - timedelta(days=days))

    assert response.status_code == 422
    assert message in response.get_json()["errors"]["json"][field][0]


def test_paying_everything_completes_the_credit(client, credit):
    remaining = credit["standing"]["remaining_total"]

    pay(client, credit["id"], remaining)
    again = pay(client, credit["id"], "1")

    assert client.get(f"{URL}/{credit['id']}").get_json()["standing"]["status"] == "completed"
    assert again.status_code == 409
    assert again.get_json()["message"] == "El crédito ya está liquidado."


def test_removing_a_payment_restores_the_balance_and_is_kept_in_the_history(client, credit):
    payment = pay(client, credit["id"], "888.49").get_json()

    response = client.delete(f"{URL}/{credit['id']}/payments/{payment['id']}")

    assert response.status_code == 204
    assert client.get(f"{URL}/{credit['id']}/payments").get_json() == []
    history = client.get(f"{URL}/{credit['id']}/history").get_json()
    assert [entry["action"] for entry in history] == ["payment_removed", "payment", "created"]
    assert history[0]["changes"]["amount"] == {"old": None, "new": "888.49"}


def test_payment_of_another_credit_is_not_found(client, credit, create_credit):
    other = create_credit(client_name="Bruno Diaz")
    payment = pay(client, credit["id"], "100").get_json()

    assert client.delete(f"{URL}/{other['id']}/payments/{payment['id']}").status_code == 404


def test_analyst_records_but_cannot_remove_payments(client, client_as, credit):
    analyst = client_as("analyst")
    viewer = client_as("viewer")

    recorded = pay(analyst, credit["id"], "100")
    removed = analyst.delete(f"{URL}/{credit['id']}/payments/{recorded.get_json()['id']}")

    assert recorded.status_code == 201
    assert removed.status_code == 403
    assert pay(viewer, credit["id"], "100").status_code == 403
    assert viewer.get(f"{URL}/{credit['id']}/payments").status_code == 200


def test_editing_a_credit_must_keep_room_for_its_payments(client, credit, valid_credit):
    pay(client, credit["id"], "1776.98", paid_on=clock.today() - timedelta(days=5))
    base = {**valid_credit, "issue_date": credit["issue_date"], "interest_rate": "12", "term_months": 12}

    later_issue = client.put(
        f"{URL}/{credit['id']}", json={**base, "amount": "10000", "issue_date": clock.today().isoformat()}
    )
    too_small = client.put(f"{URL}/{credit['id']}", json={**base, "amount": "1000"})

    assert later_issue.status_code == 422
    assert "issue_date" in later_issue.get_json()["errors"]["json"]
    assert too_small.status_code == 422
    assert "amount" in too_small.get_json()["errors"]["json"]


def test_amortization_marks_paid_and_overdue_installments(client, credit):
    pay(client, credit["id"], "888.49")

    installments = client.get(f"{URL}/{credit['id']}/amortization").get_json()["installments"]

    assert [item["status"] for item in installments[:4]] == ["paid", "overdue", "pending", "pending"]


def test_status_filter_uses_the_payments(client, credit, create_credit):
    paid_up = create_credit(client_name="Bruno Diaz", issue_date=clock.today().isoformat())

    overdue = client.get(f"{URL}?status=overdue").get_json()
    active = client.get(f"{URL}?status=active").get_json()

    assert [item["id"] for item in overdue["items"]] == [credit["id"]]
    assert [item["id"] for item in active["items"]] == [paid_up["id"]]
    assert active["meta"] == {"page": 1, "per_page": 10, "total": 1, "pages": 1}
    assert client.get(f"{URL}?status=lost").status_code == 422
