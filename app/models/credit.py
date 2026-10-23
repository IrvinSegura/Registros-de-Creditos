from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.services import amortization

if TYPE_CHECKING:
    from app.models.credit_change import CreditChange


class Credit(db.Model):
    __tablename__ = "credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(100), index=True)
    # Money and rates use fixed-point decimals to avoid float rounding errors
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    term_months: Mapped[int]
    issue_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # The ORM deletes the history itself: SQLite ignores ON DELETE CASCADE unless foreign keys are enabled
    changes: Mapped[list["CreditChange"]] = relationship(back_populates="credit", cascade="all, delete-orphan")

    @property
    def standing(self) -> amortization.Standing:
        # Derived from the payment schedule, so it is never stored and never goes stale
        return amortization.standing(self.amount, self.interest_rate, self.term_months, self.issue_date, date.today())

    def __repr__(self) -> str:
        return f"<Credit id={self.id} client_name={self.client_name!r} amount={self.amount}>"
