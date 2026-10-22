"""Business operations on credits. Knows nothing about HTTP."""

from typing import Any

from flask_sqlalchemy.pagination import Pagination

from app.errors import NotFoundError
from app.extensions import db
from app.models import Credit


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
