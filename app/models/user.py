import secrets
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercase so sign-in is case-insensitive
    username: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    # One of app.auth.permissions.ROLES
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    # Consecutive failed sign-ins; reaching the limit locks the account for a while
    failed_logins: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Identifies the user inside the session cookie instead of the id; replacing it ends every open session
    session_token: Mapped[str] = mapped_column(String(64), unique=True, default=new_session_token)

    def get_id(self) -> str:
        # Flask-Login stores this value in the session and passes it back to the user loader
        return self.session_token

    def end_sessions(self) -> None:
        self.session_token = new_session_token()

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
