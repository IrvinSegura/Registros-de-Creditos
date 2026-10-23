from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import clock
from app.extensions import db
from app.services import amortization

if TYPE_CHECKING:
    from app.models.credit_change import CreditChange
    from app.models.payment import Payment


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
    # Archived credits leave the portfolio and become read-only, but keep their data and history
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Goes up on every change; a save based on an older version is refused (see credit_service.update_credit)
    version: Mapped[int] = mapped_column(server_default="1")

    # The ORM deletes the history and payments too, so deleting works the same with or without database-level cascades
    changes: Mapped[list["CreditChange"]] = relationship(back_populates="credit", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="credit", cascade="all, delete-orphan", order_by="(Payment.paid_on, Payment.id)"
    )

    __mapper_args__ = {"version_id_col": version}

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    @property
    def paid_total(self) -> Decimal:
        return sum((payment.amount for payment in self.payments), Decimal(0))

    @property
    def standing(self) -> amortization.Standing:
        # Derived from the payment schedule and the payments, so it is never stored and never goes stale
        return amortization.standing(
            self.amount, self.interest_rate, self.term_months, self.issue_date, clock.today(), self.paid_total
        )

    def __repr__(self) -> str:
        return f"<Credit id={self.id} client_name={self.client_name!r} amount={self.amount}>"
