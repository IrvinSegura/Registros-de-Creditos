"""Business operations on credits and their payments. Knows nothing about HTTP."""

import csv
import io
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from http import HTTPStatus
from typing import Any

from sqlalchemy import Select, case, extract, func
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.exc import StaleDataError

from app import clock
from app.errors import ConflictError, DomainError, FieldError, NotFoundError
from app.extensions import db
from app.models import Credit, CreditChange, Payment
from app.services import amortization

log = logging.getLogger(__name__)

# Term buckets shown in the dashboard, in display order
TERM_RANGES = ("1-12", "13-24", "25-36", "37+")
TOP_CLIENTS_LIMIT = 5
TRACKED_FIELDS = ("client_name", "amount", "interest_rate", "term_months", "issue_date")

UPCOMING_WINDOW = timedelta(days=30)
UPCOMING_LIMIT = 5

ARCHIVED = "archived"
# Values of the status filter: the standing of the credits in the portfolio, or the archived ones
STATUSES = (amortization.ACTIVE, amortization.OVERDUE, amortization.COMPLETED, ARCHIVED)
# What each history entry records (CreditChange.action)
HISTORY_ACTIONS = ("created", "updated", "archived", "restored", "payment", "payment_removed")

# Statuses and export headers are read by end users, so they stay in Spanish
STATUS_LABELS = {
    amortization.ACTIVE: "Vigente",
    amortization.OVERDUE: "Atrasado",
    amortization.COMPLETED: "Concluido",
    ARCHIVED: "Archivado",
}


def status_of(credit: Credit) -> str:
    return ARCHIVED if credit.is_archived else credit.standing.status


# (header, value, kind): the kind tells the Excel and PDF reports how to format the value
EXPORT_COLUMNS: tuple[tuple[str, Callable[[Credit, amortization.Standing], Any], str], ...] = (
    ("ID", lambda credit, standing: credit.id, "integer"),
    ("Cliente", lambda credit, standing: credit.client_name, "text"),
    ("Monto", lambda credit, standing: credit.amount, "money"),
    ("Tasa anual (%)", lambda credit, standing: credit.interest_rate, "percent"),
    ("Plazo (meses)", lambda credit, standing: credit.term_months, "integer"),
    ("Fecha de otorgamiento", lambda credit, standing: credit.issue_date, "date"),
    ("Estado", lambda credit, standing: STATUS_LABELS[status_of(credit)], "text"),
    ("Cuota mensual", lambda credit, standing: standing.monthly_payment, "money"),
    ("Cuotas pagadas", lambda credit, standing: standing.installments_paid, "integer"),
    ("Pagado", lambda credit, standing: standing.paid_total, "money"),
    ("Saldo pendiente", lambda credit, standing: standing.outstanding_balance, "money"),
    ("Monto vencido", lambda credit, standing: standing.overdue_amount, "money"),
    ("Días de atraso", lambda credit, standing: standing.days_overdue, "integer"),
    ("Próximo vencimiento", lambda credit, standing: standing.next_due_date or "", "date"),
)


class CreditNotFoundError(NotFoundError):
    def __init__(self, credit_id: int):
        # The message reaches the end user, so it stays in Spanish
        super().__init__(f"Crédito {credit_id} no encontrado.")
        self.credit_id = credit_id


class PaymentNotFoundError(NotFoundError):
    def __init__(self, payment_id: int):
        super().__init__(f"Pago {payment_id} no encontrado.")


class ArchivedCreditError(ConflictError):
    def __init__(self):
        super().__init__("El crédito está archivado. Restáuralo para modificarlo.")


class StaleCreditError(DomainError):
    """Someone else saved the credit after this user opened it."""

    status = HTTPStatus.PRECONDITION_FAILED

    def __init__(self):
        super().__init__(
            "Otra persona modificó este crédito mientras lo editabas. Vuelve a abrirlo para ver los cambios."
        )


def _filtered_query(
    client_name: str | None = None,
    issue_date_from: date | None = None,
    issue_date_to: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    sort: str = "id",
    order: str = "asc",
    archived: bool = False,
) -> Select:
    # Payments are loaded with the credits, since every standing needs them
    query = db.select(Credit).options(selectinload(Credit.payments))
    query = query.where(Credit.archived_at.is_not(None) if archived else Credit.archived_at.is_(None))
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


def _in_portfolio(query: Select) -> Select:
    # Archived credits no longer count in the dashboard figures
    return query.where(Credit.archived_at.is_(None))


def list_credits(page: int, per_page: int, status: str | None = None, **filters: Any) -> tuple[list[Credit], int]:
    """One page of credits and how many match in total."""
    query = _filtered_query(archived=status == ARCHIVED, **filters)
    if status in (None, ARCHIVED):
        result = db.paginate(query, page=page, per_page=per_page, error_out=False)
        return list(result.items), result.total or 0
    # The standing depends on the payment schedule, so this filter runs here rather than in SQL
    matching = [credit for credit in db.session.scalars(query) if credit.standing.status == status]
    start = (page - 1) * per_page
    return matching[start:start + per_page], len(matching)


def credits_for_export(status: str | None = None, **filters: Any) -> list[Credit]:
    credits = db.session.scalars(_filtered_query(archived=status == ARCHIVED, **filters))
    if status in (None, ARCHIVED):
        return list(credits)
    return [credit for credit in credits if credit.standing.status == status]


def export_rows(credits: list[Credit]) -> list[list[Any]]:
    rows = []
    for credit in credits:
        standing = credit.standing
        rows.append([value(credit, standing) for _, value, _ in EXPORT_COLUMNS])
    return rows


def export_csv(**filters: Any) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header for header, _, _ in EXPORT_COLUMNS)
    for row in export_rows(credits_for_export(**filters)):
        writer.writerow(_serialize(value) for value in row)
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
    log.info("Credit %s created by user %s", credit.id, user_id)
    return credit


def update_credit(
    credit_id: int, data: dict[str, Any], user_id: int | None = None, expected_version: int | None = None
) -> Credit:
    """Saves the new data; with expected_version, only if nobody saved the credit since that version was read."""
    credit = get_credit(credit_id)
    _require_editable(credit)
    if expected_version is not None and expected_version != credit.version:
        raise StaleCreditError()
    _check_payments_fit(credit, data)

    changes = {}
    for field, value in data.items():
        old, new = _serialize(getattr(credit, field)), _serialize(value)
        if old != new:
            changes[field] = {"old": old, "new": new}
        setattr(credit, field, value)
    # Saving without edits leaves no history entry
    if changes:
        credit.changes.append(CreditChange(action="updated", changes=changes, user_id=user_id))
    _commit_credit()
    if changes:
        log.info("Credit %s updated by user %s: %s", credit.id, user_id, ", ".join(changes))
    return credit


def archive_credit(credit_id: int, user_id: int | None = None) -> Credit:
    credit = get_credit(credit_id)
    if credit.is_archived:
        raise ConflictError("El crédito ya está archivado.")
    credit.archived_at = datetime.now(UTC)
    credit.changes.append(CreditChange(action="archived", changes={}, user_id=user_id))
    _commit_credit()
    log.info("Credit %s archived by user %s", credit.id, user_id)
    return credit


def restore_credit(credit_id: int, user_id: int | None = None) -> Credit:
    credit = get_credit(credit_id)
    if not credit.is_archived:
        raise ConflictError("El crédito no está archivado.")
    credit.archived_at = None
    credit.changes.append(CreditChange(action="restored", changes={}, user_id=user_id))
    _commit_credit()
    log.info("Credit %s restored by user %s", credit.id, user_id)
    return credit


def delete_credit(credit_id: int, user_id: int | None = None) -> None:
    """Removes an archived credit for good, with its payments and history."""
    credit = get_credit(credit_id)
    # Two deliberate steps, so a credit is never lost by a single click
    if not credit.is_archived:
        raise ConflictError("Archiva el crédito antes de eliminarlo definitivamente.")
    db.session.delete(credit)
    db.session.commit()
    log.warning("Credit %s permanently deleted by user %s", credit_id, user_id)


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
    standing, today = credit.standing, clock.today()
    total_paid = sum((installment.payment for installment in schedule), Decimal(0))
    return {
        "monthly_payment": schedule[0].payment,
        "total_interest": total_paid - credit.amount,
        "total_paid": total_paid,
        "installments": [
            {**vars(installment), "status": amortization.installment_status(installment, standing, today)}
            for installment in schedule
        ],
    }


def get_quote(amount: Decimal, interest_rate: Decimal, term_months: int) -> dict[str, Decimal]:
    return amortization.quote(amount, interest_rate, term_months, clock.today())


def list_payments(credit_id: int) -> list[Payment]:
    get_credit(credit_id)
    query = (
        db.select(Payment)
        .options(joinedload(Payment.user))
        .where(Payment.credit_id == credit_id)
        .order_by(Payment.paid_on.desc(), Payment.id.desc())
    )
    return list(db.session.scalars(query))


def record_payment(credit_id: int, data: dict[str, Any], user_id: int | None = None) -> Payment:
    credit = get_credit(credit_id)
    _require_editable(credit)
    if data["paid_on"] < credit.issue_date:
        raise FieldError("paid_on", "La fecha de pago no puede ser anterior al otorgamiento del crédito.")
    remaining = credit.standing.remaining_total
    if remaining == 0:
        raise ConflictError("El crédito ya está liquidado.")
    if data["amount"] > remaining:
        raise FieldError("amount", f"El pago supera lo que falta por pagar (${remaining:,.2f}).")

    payment = Payment(**data, user_id=user_id)
    credit.payments.append(payment)
    credit.changes.append(CreditChange(action="payment", changes=_payment_changes(payment), user_id=user_id))
    db.session.commit()
    log.info("Payment %s of %s recorded on credit %s by user %s", payment.id, payment.amount, credit.id, user_id)
    return payment


def delete_payment(credit_id: int, payment_id: int, user_id: int | None = None) -> None:
    """Undoes a payment recorded by mistake; the history keeps a trace of it."""
    credit = get_credit(credit_id)
    _require_editable(credit)
    payment = db.session.get(Payment, payment_id)
    if payment is None or payment.credit_id != credit.id:
        raise PaymentNotFoundError(payment_id)
    credit.changes.append(CreditChange(action="payment_removed", changes=_payment_changes(payment), user_id=user_id))
    credit.payments.remove(payment)
    db.session.commit()
    log.warning("Payment %s of %s removed from credit %s by user %s", payment_id, payment.amount, credit.id, user_id)


def get_summary(issue_date_from: date | None = None, issue_date_to: date | None = None) -> dict[str, Any]:
    """Portfolio totals and breakdowns, optionally limited to an issue-date period."""

    def in_period(query: Select) -> Select:
        return _in_portfolio(_apply_date_range(query, issue_date_from, issue_date_to))

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

    # "Ana Paz" and "Ana paz" are the same client; min() shows the capitalized spelling when both exist
    client_key = func.lower(Credit.client_name)
    client_name = func.min(Credit.client_name)
    client_total = func.sum(Credit.amount)
    top_clients = db.session.execute(
        in_period(db.select(client_name, func.count(Credit.id), client_total))
        .group_by(client_key)
        .order_by(client_total.desc(), client_name)
        .limit(TOP_CLIENTS_LIMIT)
    ).all()

    credits = db.session.scalars(in_period(db.select(Credit).options(selectinload(Credit.payments))))
    portfolio = _portfolio_standing(credits, clock.today())

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
    """Totals that depend on each credit's payment schedule and payments, so they are computed here rather than in SQL."""
    counts = {status: 0 for status in (amortization.ACTIVE, amortization.OVERDUE, amortization.COMPLETED)}
    outstanding = overdue_amount = paid = weighted_rate = amount_sum = Decimal(0)
    upcoming = []
    for credit in credits:
        standing = credit.standing
        counts[standing.status] += 1
        outstanding += standing.outstanding_balance
        overdue_amount += standing.overdue_amount
        paid += standing.paid_total
        weighted_rate += credit.amount * credit.interest_rate
        amount_sum += credit.amount
        # Overdue installments are already past the window's start, so they always make the list
        if standing.status != amortization.COMPLETED and standing.next_due_date <= today + UPCOMING_WINDOW:
            overdue = standing.status == amortization.OVERDUE
            upcoming.append(
                {
                    "credit_id": credit.id,
                    "client_name": credit.client_name,
                    "due_date": standing.next_due_date,
                    "amount": standing.overdue_amount if overdue else standing.next_payment,
                    "overdue": overdue,
                }
            )

    upcoming.sort(key=lambda payment: (payment["due_date"], payment["client_name"]))
    return {
        "active_credits": counts[amortization.ACTIVE],
        "overdue_credits": counts[amortization.OVERDUE],
        "completed_credits": counts[amortization.COMPLETED],
        "outstanding_balance": outstanding,
        "overdue_amount": overdue_amount,
        "paid_total": paid,
        "weighted_interest_rate": weighted_rate / amount_sum if amount_sum else Decimal(0),
        "upcoming_payments": upcoming[:UPCOMING_LIMIT],
    }


def _require_editable(credit: Credit) -> None:
    if credit.is_archived:
        raise ArchivedCreditError()


def _check_payments_fit(credit: Credit, data: dict[str, Any]) -> None:
    """New terms must still make sense for the payments already recorded."""
    if not credit.payments:
        return
    first_payment = min(payment.paid_on for payment in credit.payments)
    if data["issue_date"] > first_payment:
        raise FieldError(
            "issue_date",
            f"Hay pagos registrados desde el {first_payment:%d/%m/%Y}; el otorgamiento no puede ser posterior.",
        )
    total = amortization.total_due(data["amount"], data["interest_rate"], data["term_months"], data["issue_date"])
    if credit.paid_total > total:
        raise FieldError("amount", "Los pagos registrados superan el total a pagar con estos datos.")


def _commit_credit() -> None:
    # The version check in the UPDATE fails when another request saved the credit in between
    try:
        db.session.commit()
    except StaleDataError:
        db.session.rollback()
        raise StaleCreditError() from None


def _payment_changes(payment: Payment) -> dict[str, Any]:
    changes = {
        "amount": {"old": None, "new": _serialize(payment.amount)},
        "paid_on": {"old": None, "new": _serialize(payment.paid_on)},
    }
    if payment.note:
        changes["note"] = {"old": None, "new": payment.note}
    return changes


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
