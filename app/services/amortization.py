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


def quote(amount: Decimal, annual_rate_percent: Decimal, months: int) -> dict[str, Decimal]:
    payment = monthly_payment(amount, annual_rate_percent, months)
    # Totals come from the schedule so they include the last-installment adjustment
    schedule = build_schedule(amount, annual_rate_percent, months, date.today())
    total_paid = sum((installment.payment for installment in schedule), Decimal(0))
    return {
        "monthly_payment": payment,
        "total_interest": total_paid - Decimal(amount),
        "total_paid": total_paid,
    }
