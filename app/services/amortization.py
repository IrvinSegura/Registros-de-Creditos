"""Fixed-payment (French) amortization, computed with exact decimals."""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class Installment:
    number: int
    due_date: date
    payment: Decimal
    interest: Decimal
    principal: Decimal
    balance: Decimal


def _round(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_rate(annual_rate_percent: Decimal) -> Decimal:
    # The stored interest rate is a yearly percentage, paid monthly
    return Decimal(annual_rate_percent) / 100 / MONTHS_PER_YEAR


def monthly_payment(amount: Decimal, annual_rate_percent: Decimal, months: int) -> Decimal:
    rate = monthly_rate(annual_rate_percent)
    if rate == 0:
        return _round(Decimal(amount) / months)
    factor = (1 + rate) ** months
    return _round(Decimal(amount) * rate * factor / (factor - 1))


def add_months(start: date, months: int) -> date:
    # Keeps the day of the month, clamped to the last day of shorter months
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def build_schedule(amount: Decimal, annual_rate_percent: Decimal, months: int, start: date) -> list[Installment]:
    rate = monthly_rate(annual_rate_percent)
    payment = monthly_payment(amount, annual_rate_percent, months)
    balance = Decimal(amount)
    schedule = []

    for number in range(1, months + 1):
        interest = _round(balance * rate)
        principal = payment - interest
        # The last installment absorbs the rounding so the balance ends exactly at zero
        if number == months:
            principal = balance
        balance -= principal
        schedule.append(
            Installment(
                number=number,
                due_date=add_months(start, number),
                payment=principal + interest,
                interest=interest,
                principal=principal,
                balance=balance,
            )
        )
    return schedule


def quote(amount: Decimal, annual_rate_percent: Decimal, months: int, start: date) -> dict[str, Decimal]:
    payment = monthly_payment(amount, annual_rate_percent, months)
    # Totals come from the schedule so they include the last-installment adjustment
    schedule = build_schedule(amount, annual_rate_percent, months, start)
    total_paid = sum((installment.payment for installment in schedule), Decimal(0))
    return {
        "monthly_payment": payment,
        "total_interest": total_paid - Decimal(amount),
        "total_paid": total_paid,
    }


@dataclass(frozen=True)
class Standing:
    """Where a credit stands on a given day, given what has been paid so far.

    Payments cover the installments in order; a partial payment goes to interest first, then principal.
    """

    status: str
    installments_elapsed: int
    installments_paid: int
    paid_total: Decimal
    remaining_total: Decimal
    outstanding_balance: Decimal
    next_due_date: date | None
    next_payment: Decimal | None
    monthly_payment: Decimal
    overdue_installments: int
    overdue_amount: Decimal
    days_overdue: int


ACTIVE = "active"
OVERDUE = "overdue"
COMPLETED = "completed"
# States of a single installment
PAID = "paid"
PENDING = "pending"


def standing(
    amount: Decimal, annual_rate_percent: Decimal, months: int, start: date, today: date, paid_total: Decimal = Decimal(0)
) -> Standing:
    schedule = build_schedule(amount, annual_rate_percent, months, start)
    # Installments due today count as elapsed, but only become overdue the day after
    elapsed = sum(1 for installment in schedule if installment.due_date <= today)
    past_due = [installment for installment in schedule if installment.due_date < today]

    left = Decimal(paid_total)
    balance = _round(Decimal(amount))
    paid_installments = 0
    upcoming, upcoming_left = None, None
    for installment in schedule:
        if left >= installment.payment:
            left -= installment.payment
            balance = installment.balance
            paid_installments += 1
            continue
        balance -= max(Decimal(0), left - installment.interest)
        upcoming, upcoming_left = installment, installment.payment - left
        break

    overdue_installments = max(0, len(past_due) - paid_installments)
    total = sum((installment.payment for installment in schedule), Decimal(0))
    if upcoming is None:
        status = COMPLETED
    else:
        status = OVERDUE if overdue_installments else ACTIVE
    return Standing(
        status=status,
        installments_elapsed=elapsed,
        installments_paid=paid_installments,
        paid_total=_round(Decimal(paid_total)),
        remaining_total=max(Decimal(0), total - Decimal(paid_total)),
        outstanding_balance=balance,
        next_due_date=upcoming.due_date if upcoming else None,
        next_payment=upcoming_left,
        monthly_payment=schedule[0].payment,
        overdue_installments=overdue_installments,
        overdue_amount=max(Decimal(0), sum((installment.payment for installment in past_due), Decimal(0)) - paid_total),
        days_overdue=(today - upcoming.due_date).days if overdue_installments else 0,
    )


def total_due(amount: Decimal, annual_rate_percent: Decimal, months: int, start: date) -> Decimal:
    """Everything the borrower pays over the life of the credit."""
    return sum((installment.payment for installment in build_schedule(amount, annual_rate_percent, months, start)), Decimal(0))


def installment_status(installment: Installment, credit_standing: Standing, today: date) -> str:
    if installment.number <= credit_standing.installments_paid:
        return PAID
    return OVERDUE if installment.due_date < today else PENDING
