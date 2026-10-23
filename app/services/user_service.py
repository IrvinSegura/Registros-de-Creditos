"""User accounts: creation, password changes and sign-in checks. Knows nothing about HTTP."""

import re
from datetime import UTC, datetime, timedelta
from functools import cache
from http import HTTPStatus

from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.permissions import ROLES
from app.errors import DomainError
from app.extensions import db
from app.models import User

MAX_FAILED_LOGINS = 5
LOCK_DURATION = timedelta(minutes=15)
MIN_PASSWORD_LENGTH = 10
USERNAME_REGEX = re.compile(r"^[a-z0-9._-]{3,50}$")


# Messages reach the end user (sign-in page or CLI), so they stay in Spanish
class UserError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    status = HTTPStatus.UNAUTHORIZED

    def __init__(self):
        super().__init__("Usuario o contraseña incorrectos.")


class AccountLockedError(DomainError):
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, minutes: int):
        super().__init__(
            f"La cuenta se bloqueó por varios intentos fallidos. Intenta de nuevo en {minutes} "
            f"{'minuto' if minutes == 1 else 'minutos'}."
        )


def normalize_username(username: str) -> str:
    return username.strip().lower()


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def find_user(username: str) -> User | None:
    return db.session.scalar(db.select(User).where(User.username == normalize_username(username)))


def list_users() -> list[User]:
    return list(db.session.scalars(db.select(User).order_by(User.username)))


def create_user(username: str, full_name: str, password: str, role: str) -> User:
    username = normalize_username(username)
    full_name = " ".join(full_name.split())
    if not USERNAME_REGEX.match(username):
        raise UserError("El usuario debe tener de 3 a 50 caracteres: letras minúsculas, números, punto, guion o guion bajo.")
    if find_user(username):
        raise UserError(f"El usuario '{username}' ya existe.")
    if not 3 <= len(full_name) <= 100:
        raise UserError("El nombre debe tener entre 3 y 100 caracteres.")
    if role not in ROLES:
        raise UserError(f"Rol desconocido. Usa uno de: {', '.join(ROLES)}.")
    _check_password(password)

    user = User(username=username, full_name=full_name, password_hash=generate_password_hash(password), role=role)
    db.session.add(user)
    db.session.commit()
    return user


def set_password(username: str, password: str) -> User:
    user = _require_user(username)
    _check_password(password)
    user.password_hash = generate_password_hash(password)
    # A new password also lifts any lock
    user.failed_logins = 0
    user.locked_until = None
    db.session.commit()
    return user


def set_active(username: str, active: bool) -> User:
    user = _require_user(username)
    user.is_active = active
    db.session.commit()
    return user


def authenticate(username: str, password: str) -> User:
    """Returns the user when the password matches; raises otherwise and counts the failure."""
    user = find_user(username)
    if user is None or not user.is_active:
        # Hash anyway so unknown and known usernames take the same time to answer
        check_password_hash(_dummy_hash(), password)
        raise InvalidCredentialsError()

    now = datetime.now(UTC)
    if user.locked_until and _as_utc(user.locked_until) > now:
        raise AccountLockedError(_minutes_left(user.locked_until, now))

    if not check_password_hash(user.password_hash, password):
        user.failed_logins += 1
        locked = user.failed_logins >= MAX_FAILED_LOGINS
        if locked:
            user.failed_logins = 0
            user.locked_until = now + LOCK_DURATION
        db.session.commit()
        if locked:
            raise AccountLockedError(_minutes_left(user.locked_until, now))
        raise InvalidCredentialsError()

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = now
    db.session.commit()
    return user


def _require_user(username: str) -> User:
    user = find_user(username)
    if user is None:
        raise UserError(f"El usuario '{normalize_username(username)}' no existe.")
    return user


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")


@cache
def _dummy_hash() -> str:
    return generate_password_hash("not-a-real-password")


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; they were stored in UTC
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _minutes_left(locked_until: datetime, now: datetime) -> int:
    return max(1, -(-int((_as_utc(locked_until) - now).total_seconds()) // 60))
