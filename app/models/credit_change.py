from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.models.credit import Credit


class CreditChange(db.Model):
    """Audit entry: one row each time a credit is created or edited."""

    __tablename__ = "credit_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("credits.id", ondelete="CASCADE"), index=True)
    # "created" or "updated"
    action: Mapped[str] = mapped_column(String(20))
    # {field: {"old": value, "new": value}}, values stored as JSON-friendly strings
    changes: Mapped[dict[str, Any]] = mapped_column(JSON)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    credit: Mapped["Credit"] = relationship(back_populates="changes")
