from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class LoginAttempt(db.Model):
    """One row per sign-in attempt: limits attempts per address and keeps a sign-in log."""

    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Long enough for IPv6 addresses
    ip_address: Mapped[str] = mapped_column(String(45), index=True)
    # As typed, so attempts on accounts that do not exist are logged too
    username: Mapped[str] = mapped_column(String(50))
    succeeded: Mapped[bool]
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    def __repr__(self) -> str:
        return f"<LoginAttempt ip={self.ip_address!r} username={self.username!r} succeeded={self.succeeded}>"
