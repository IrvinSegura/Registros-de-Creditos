from datetime import date
from decimal import Decimal

from app.services import amortization


def test_monthly_payment_uses_the_fixed_payment_formula():
    # 10,000 at 12% a year over 12 months -> 888.49 per month
    assert amortization.monthly_payment(Decimal("10000"), Decimal("12"), 12) == Decimal("888.49")


def test_schedule_ends_with_a_zero_balance():
    schedule = amortization.build_schedule(Decimal("10000"), Decimal("12"), 12, date(2026, 1, 15))

    assert len(schedule) == 12
    assert schedule[0].interest == Decimal("100.00")
    assert schedule[0].principal == Decimal("788.49")
    assert schedule[-1].balance == Decimal("0.00")
    assert sum(i.principal for i in schedule) == Decimal("10000")


def test_last_installment_absorbs_rounding():
    schedule = amortization.build_schedule(Decimal("1000"), Decimal("7.5"), 7, date(2026, 1, 1))

    regular = {i.payment for i in schedule[:-1]}
    assert len(regular) == 1
    assert abs(schedule[-1].payment - regular.pop()) <= Decimal("0.05")
    assert schedule[-1].balance == 0


def test_due_dates_keep_the_day_and_clamp_short_months():
    schedule = amortization.build_schedule(Decimal("3000"), Decimal("10"), 3, date(2026, 1, 31))

    assert [i.due_date for i in schedule] == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_quote_totals():
    result = amortization.quote(Decimal("10000"), Decimal("12"), 12)

    assert result["monthly_payment"] == Decimal("888.49")
    assert result["total_paid"] == result["total_interest"] + Decimal("10000")
    assert result["total_interest"] == Decimal("661.86")
