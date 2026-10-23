from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.models.credit import Credit
    from app.models.user import User


class Payment(db.Model):
    """Money received for a credit; payments cover its installments in order."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("credits.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(200), default="", server_default="")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Who recorded it; empty for payments carried over when payment tracking started or whose user was removed
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    credit: Mapped["Credit"] = relationship(back_populates="payments")
    user: Mapped["User | None"] = relationship()

    def __repr__(self) -> str:
        return f"<Payment id={self.id} credit_id={self.credit_id} amount={self.amount} paid_on={self.paid_on}>"
