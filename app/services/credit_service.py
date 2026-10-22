"""Business operations on credits. Knows nothing about HTTP."""

from decimal import Decimal
from typing import Any

from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import case, extract, func

from app.errors import NotFoundError
from app.extensions import db
from app.models import Credit


# Term buckets shown in the dashboard, in display order
TERM_RANGES = ("1-12", "13-24", "25-36", "37+")


class CreditNotFoundError(NotFoundError):
    def __init__(self, credit_id: int):
        # The message reaches the end user, so it stays in Spanish
        super().__init__(f"Crédito {credit_id} no encontrado.")
        self.credit_id = credit_id


def list_credits(page: int, per_page: int, client_name: str | None = None) -> Pagination:
    query = db.select(Credit).order_by(Credit.id)
    if client_name:
        query = query.where(Credit.client_name.icontains(client_name, autoescape=True))
    return db.paginate(query, page=page, per_page=per_page, error_out=False)


def get_credit(credit_id: int) -> Credit:
    credit = db.session.get(Credit, credit_id)
    if credit is None:
        raise CreditNotFoundError(credit_id)
    return credit


def create_credit(data: dict[str, Any]) -> Credit:
    credit = Credit(**data)
    db.session.add(credit)
    db.session.commit()
    return credit


def update_credit(credit_id: int, data: dict[str, Any]) -> Credit:
    credit = get_credit(credit_id)
    for field, value in data.items():
        setattr(credit, field, value)
    db.session.commit()
    return credit


def delete_credit(credit_id: int) -> None:
    credit = get_credit(credit_id)
    db.session.delete(credit)
    db.session.commit()


def get_summary() -> dict[str, Any]:
    """Portfolio totals, monthly issued amounts and credit counts per term range."""
    count, total_amount, rate_sum, term_sum = db.session.execute(
        db.select(
            func.count(Credit.id),
            func.sum(Credit.amount),
            func.sum(Credit.interest_rate),
            func.sum(Credit.term_months),
        )
    ).one()
    total_amount, rate_sum, term_sum = (_to_decimal(value) for value in (total_amount, rate_sum, term_sum))

    year = extract("year", Credit.issue_date)
    month = extract("month", Credit.issue_date)
    monthly = db.session.execute(
        db.select(year, month, func.count(Credit.id), func.sum(Credit.amount))
        .group_by(year, month)
        .order_by(year, month)
    ).all()

    term_range = case(
        (Credit.term_months <= 12, TERM_RANGES[0]),
        (Credit.term_months <= 24, TERM_RANGES[1]),
        (Credit.term_months <= 36, TERM_RANGES[2]),
        else_=TERM_RANGES[3],
    )
    by_term = dict(db.session.execute(db.select(term_range, func.count(Credit.id)).group_by(term_range)).all())

    return {
        "total_credits": count,
        "total_amount": total_amount,
        "average_amount": total_amount / count if count else Decimal(0),
        "average_interest_rate": rate_sum / count if count else Decimal(0),
        "average_term_months": term_sum / count if count else Decimal(0),
        "monthly": [
            {"year": int(y), "month": int(m), "credits": credits, "total_amount": _to_decimal(amount)}
            for y, m, credits, amount in monthly
        ],
        "by_term": [{"range": label, "credits": by_term.get(label, 0)} for label in TERM_RANGES],
    }


def _to_decimal(value: Any) -> Decimal:
    # SQLite returns aggregates as floats; going through str keeps the exact digits
    return Decimal(str(value)) if value is not None else Decimal(0)
