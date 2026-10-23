"""Business operations on credits. Knows nothing about HTTP."""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import Select, case, extract, func
from sqlalchemy.orm import joinedload

from app.errors import NotFoundError
from app.extensions import db
from app.models import Credit, CreditChange
from app.services import amortization

# Term buckets shown in the dashboard, in display order
TERM_RANGES = ("1-12", "13-24", "25-36", "37+")
TOP_CLIENTS_LIMIT = 5
TRACKED_FIELDS = ("client_name", "amount", "interest_rate", "term_months", "issue_date")

UPCOMING_WINDOW = timedelta(days=30)
UPCOMING_LIMIT = 5

# CSV headers and statuses are read by end users, so they stay in Spanish
STATUS_LABELS = {amortization.ACTIVE: "Vigente", amortization.COMPLETED: "Concluido"}
CSV_COLUMNS = (
    ("ID", lambda credit, standing: credit.id),
    ("Cliente", lambda credit, standing: credit.client_name),
    ("Monto", lambda credit, standing: credit.amount),
    ("Tasa anual (%)", lambda credit, standing: credit.interest_rate),
    ("Plazo (meses)", lambda credit, standing: credit.term_months),
    ("Fecha de otorgamiento", lambda credit, standing: credit.issue_date),
    ("Estado", lambda credit, standing: STATUS_LABELS[standing.status]),
    ("Cuota mensual", lambda credit, standing: standing.monthly_payment),
    ("Cuotas transcurridas", lambda credit, standing: standing.installments_elapsed),
    ("Saldo pendiente", lambda credit, standing: standing.outstanding_balance),
    ("Próximo vencimiento", lambda credit, standing: standing.next_due_date or ""),
)


class CreditNotFoundError(NotFoundError):
    def __init__(self, credit_id: int):
        # The message reaches the end user, so it stays in Spanish
        super().__init__(f"Crédito {credit_id} no encontrado.")
        self.credit_id = credit_id


def _filtered_query(
    client_name: str | None = None,
    issue_date_from: date | None = None,
    issue_date_to: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    sort: str = "id",
    order: str = "asc",
) -> Select:
    query = db.select(Credit)
    if client_name:
        query = query.where(Credit.client_name.icontains(client_name, autoescape=True))
    query = _apply_date_range(query, issue_date_from, issue_date_to)
    if amount_min is not None:
        query = query.where(Credit.amount >= amount_min)
    if amount_max is not None:
        query = query.where(Credit.amount <= amount_max)

    column = getattr(Credit, sort)
    # The id tie-breaker keeps pagination stable when sorted values repeat
    return query.order_by(column.desc() if order == "desc" else column.asc(), Credit.id)


def _apply_date_range(query: Select, issue_date_from: date | None, issue_date_to: date | None) -> Select:
    if issue_date_from:
        query = query.where(Credit.issue_date >= issue_date_from)
    if issue_date_to:
        query = query.where(Credit.issue_date <= issue_date_to)
    return query


def list_credits(page: int, per_page: int, **filters: Any) -> Pagination:
    return db.paginate(_filtered_query(**filters), page=page, per_page=per_page, error_out=False)


def export_csv(**filters: Any) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header for header, _ in CSV_COLUMNS)
    for credit in db.session.scalars(_filtered_query(**filters)):
        standing = credit.standing
        writer.writerow(_serialize(value(credit, standing)) for _, value in CSV_COLUMNS)
    # The BOM lets Excel detect UTF-8 so accented names display correctly
    return "﻿" + buffer.getvalue()


def get_credit(credit_id: int) -> Credit:
    credit = db.session.get(Credit, credit_id)
    if credit is None:
        raise CreditNotFoundError(credit_id)
    return credit


def create_credit(data: dict[str, Any], user_id: int | None = None) -> Credit:
    credit = Credit(**data)
    changes = {field: {"old": None, "new": _serialize(data[field])} for field in TRACKED_FIELDS}
    credit.changes.append(CreditChange(action="created", changes=changes, user_id=user_id))
    db.session.add(credit)
    db.session.commit()
    return credit


def update_credit(credit_id: int, data: dict[str, Any], user_id: int | None = None) -> Credit:
    credit = get_credit(credit_id)
    changes = {}
    for field, value in data.items():
        old, new = _serialize(getattr(credit, field)), _serialize(value)
        if old != new:
            changes[field] = {"old": old, "new": new}
        setattr(credit, field, value)
    # Saving without edits leaves no history entry
    if changes:
        credit.changes.append(CreditChange(action="updated", changes=changes, user_id=user_id))
    db.session.commit()
    return credit


def delete_credit(credit_id: int) -> None:
    credit = get_credit(credit_id)
    db.session.delete(credit)
    db.session.commit()


def get_history(credit_id: int) -> list[CreditChange]:
    get_credit(credit_id)
    query = (
        db.select(CreditChange)
        .options(joinedload(CreditChange.user))
        .where(CreditChange.credit_id == credit_id)
        .order_by(CreditChange.changed_at.desc(), CreditChange.id.desc())
    )
    return list(db.session.scalars(query))


def get_amortization(credit_id: int) -> dict[str, Any]:
    credit = get_credit(credit_id)
    schedule = amortization.build_schedule(credit.amount, credit.interest_rate, credit.term_months, credit.issue_date)
    total_paid = sum((installment.payment for installment in schedule), Decimal(0))
    return {
        "monthly_payment": schedule[0].payment,
        "total_interest": total_paid - credit.amount,
        "total_paid": total_paid,
        "installments": schedule,
    }


def get_quote(amount: Decimal, interest_rate: Decimal, term_months: int) -> dict[str, Decimal]:
    return amortization.quote(amount, interest_rate, term_months)


def get_summary(issue_date_from: date | None = None, issue_date_to: date | None = None) -> dict[str, Any]:
    """Portfolio totals and breakdowns, optionally limited to an issue-date period."""

    def in_period(query: Select) -> Select:
        return _apply_date_range(query, issue_date_from, issue_date_to)

    count, total_amount, rate_sum, term_sum = db.session.execute(
        in_period(
            db.select(
                func.count(Credit.id),
                func.sum(Credit.amount),
                func.sum(Credit.interest_rate),
                func.sum(Credit.term_months),
            )
        )
    ).one()
    total_amount, rate_sum, term_sum = (_to_decimal(value) for value in (total_amount, rate_sum, term_sum))

    year = extract("year", Credit.issue_date)
    month = extract("month", Credit.issue_date)
    monthly = db.session.execute(
        in_period(db.select(year, month, func.count(Credit.id), func.sum(Credit.amount)))
        .group_by(year, month)
        .order_by(year, month)
    ).all()

    term_range = case(
        (Credit.term_months <= 12, TERM_RANGES[0]),
        (Credit.term_months <= 24, TERM_RANGES[1]),
        (Credit.term_months <= 36, TERM_RANGES[2]),
        else_=TERM_RANGES[3],
    )
    by_term = dict(db.session.execute(in_period(db.select(term_range, func.count(Credit.id))).group_by(term_range)).all())

    client_total = func.sum(Credit.amount)
    top_clients = db.session.execute(
        in_period(db.select(Credit.client_name, func.count(Credit.id), client_total))
        .group_by(Credit.client_name)
        .order_by(client_total.desc(), Credit.client_name)
        .limit(TOP_CLIENTS_LIMIT)
    ).all()

    portfolio = _portfolio_standing(db.session.scalars(in_period(db.select(Credit))), date.today())

    return {
        "total_credits": count,
        **portfolio,
        "total_amount": total_amount,
        "average_amount": total_amount / count if count else Decimal(0),
        "average_interest_rate": rate_sum / count if count else Decimal(0),
        "average_term_months": term_sum / count if count else Decimal(0),
        "monthly": [
            {"year": int(y), "month": int(m), "credits": credits, "total_amount": _to_decimal(amount)}
            for y, m, credits, amount in monthly
        ],
        "by_term": [{"range": label, "credits": by_term.get(label, 0)} for label in TERM_RANGES],
        "top_clients": [
            {"client_name": name, "credits": credits, "total_amount": _to_decimal(amount)}
            for name, credits, amount in top_clients
        ],
    }


def _portfolio_standing(credits, today: date) -> dict[str, Any]:
    """Totals that depend on each credit's payment schedule, so they are computed here rather than in SQL."""
    active = completed = 0
    outstanding = weighted_rate = amount_sum = Decimal(0)
    upcoming = []
    for credit in credits:
        standing = credit.standing
        outstanding += standing.outstanding_balance
        weighted_rate += credit.amount * credit.interest_rate
        amount_sum += credit.amount
        if standing.status == amortization.COMPLETED:
            completed += 1
            continue
        active += 1
        if standing.next_due_date <= today + UPCOMING_WINDOW:
            upcoming.append(
                {
                    "credit_id": credit.id,
                    "client_name": credit.client_name,
                    "due_date": standing.next_due_date,
                    "amount": standing.next_payment,
                }
            )

    upcoming.sort(key=lambda payment: (payment["due_date"], payment["client_name"]))
    return {
        "active_credits": active,
        "completed_credits": completed,
        "outstanding_balance": outstanding,
        "weighted_interest_rate": weighted_rate / amount_sum if amount_sum else Decimal(0),
        "upcoming_payments": upcoming[:UPCOMING_LIMIT],
    }


def _serialize(value: Any) -> Any:
    # JSON and CSV friendly: decimals with two places, dates in ISO format
    if isinstance(value, Decimal):
        return str(value.quantize(Decimal("0.01")))
    if isinstance(value, date):
        return value.isoformat()
    return value


def _to_decimal(value: Any) -> Decimal:
    # SQLite returns aggregates as floats; going through str keeps the exact digits
    return Decimal(str(value)) if value is not None else Decimal(0)
