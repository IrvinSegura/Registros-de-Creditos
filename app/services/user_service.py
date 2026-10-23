"""User accounts: creation, administration, password changes and sign-in checks. Knows nothing about HTTP."""

import logging
import re
from datetime import UTC, datetime, timedelta
from functools import cache
from http import HTTPStatus

from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.permissions import ADMIN, ROLES
from app.errors import DomainError, FieldError, NotFoundError
from app.extensions import db
from app.models import LoginAttempt, User

log = logging.getLogger(__name__)

MAX_FAILED_LOGINS = 5
LOCK_DURATION = timedelta(minutes=15)
# Per network address, so trying many usernames (or one password on every account) is also slowed down
MAX_FAILED_PER_ADDRESS = 10
ADDRESS_WINDOW = timedelta(minutes=15)
LOGIN_LOG_RETENTION = timedelta(days=90)
MIN_PASSWORD_LENGTH = 10
USERNAME_REGEX = re.compile(r"^[a-z0-9._-]{3,50}$")


# Messages reach the end user (pages, forms or CLI), so they stay in Spanish
class UserError(FieldError):
    """Invalid account data; `field` names the form field it belongs to."""


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: int):
        super().__init__(f"Usuario {user_id} no encontrado.")


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


class TooManyAttemptsError(DomainError):
    status = HTTPStatus.TOO_MANY_REQUESTS

    def __init__(self, minutes: int):
        super().__init__(
            f"Demasiados intentos fallidos desde esta conexión. Intenta de nuevo en {minutes} "
            f"{'minuto' if minutes == 1 else 'minutos'}."
        )


def normalize_username(username: str) -> str:
    return username.strip().lower()


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def require_user_by_id(user_id: int) -> User:
    user = get_user(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


def find_by_session_token(token: str) -> User | None:
    return db.session.scalar(db.select(User).where(User.session_token == token))


def find_user(username: str) -> User | None:
    return db.session.scalar(db.select(User).where(User.username == normalize_username(username)))


def list_users() -> list[User]:
    return list(db.session.scalars(db.select(User).order_by(User.username)))


def create_user(username: str, full_name: str, password: str, role: str) -> User:
    username = normalize_username(username)
    full_name = _clean_name(full_name)
    if not USERNAME_REGEX.match(username):
        raise UserError(
            "username", "El usuario debe tener de 3 a 50 caracteres: letras minúsculas, números, punto, guion o guion bajo."
        )
    if find_user(username):
        raise UserError("username", f"El usuario '{username}' ya existe.")
    _check_role(role)
    _check_password(password)

    user = User(username=username, full_name=full_name, password_hash=generate_password_hash(password), role=role)
    db.session.add(user)
    db.session.commit()
    log.info("User %s created with role %s", user.username, user.role)
    return user


def update_user(user_id: int, full_name: str, role: str, is_active: bool, acting_user: User) -> User:
    """Changes an account from the users page. Administrators cannot demote or deactivate themselves."""
    user = require_user_by_id(user_id)
    full_name = _clean_name(full_name)
    _check_role(role)
    if user.id == acting_user.id and role != ADMIN:
        raise UserError("role", "No puedes quitarte el rol de administrador.")
    if user.id == acting_user.id and not is_active:
        raise UserError("is_active", "No puedes desactivar tu propia cuenta.")

    user.full_name, user.role = full_name, role
    if user.is_active and not is_active:
        user.end_sessions()
    user.is_active = is_active
    db.session.commit()
    log.info("User %s updated by %s: role=%s active=%s", user.username, acting_user.username, role, is_active)
    return user


def reset_password(user_id: int, password: str, acting_user: User) -> User:
    user = set_password(require_user_by_id(user_id).username, password)
    log.info("Password of %s reset by %s", user.username, acting_user.username)
    return user


def change_own_password(user: User, current_password: str, new_password: str) -> User:
    """The signed-in user's own change; ends their sessions everywhere (the caller signs this one in again)."""
    if not check_password_hash(user.password_hash, current_password):
        raise UserError("current_password", "La contraseña actual no es correcta.")
    if current_password == new_password:
        raise UserError("new_password", "La nueva contraseña debe ser distinta de la actual.")
    _check_password(new_password, field="new_password")
    user.password_hash = generate_password_hash(new_password)
    user.end_sessions()
    db.session.commit()
    log.info("User %s changed their password", user.username)
    return user


def set_password(username: str, password: str) -> User:
    user = _require_user(username)
    _check_password(password)
    user.password_hash = generate_password_hash(password)
    # A new password also lifts any lock and signs the account out everywhere
    user.failed_logins = 0
    user.locked_until = None
    user.end_sessions()
    db.session.commit()
    return user


def set_active(username: str, active: bool) -> User:
    user = _require_user(username)
    user.is_active = active
    if not active:
        user.end_sessions()
    db.session.commit()
    return user


def end_sessions(username: str) -> User:
    """Signs the user out of every browser without changing the password."""
    user = _require_user(username)
    user.end_sessions()
    db.session.commit()
    log.info("Sessions of %s ended", user.username)
    return user


def authenticate(username: str, password: str, client_ip: str) -> User:
    """Returns the user when the password matches; raises otherwise.

    Every attempt is logged. Too many failures from one address block it for a while, whatever
    usernames were tried; too many failures on one account lock that account.
    """
    now = datetime.now(UTC)
    _check_address(client_ip, now)
    try:
        user = _check_credentials(username, password, now)
    except (InvalidCredentialsError, AccountLockedError) as failure:
        _log_attempt(client_ip, username, False, now)
        log.warning("Failed sign-in for %r from %s: %s", username.strip()[:50], client_ip, type(failure).__name__)
        raise
    _log_attempt(client_ip, username, True, now)
    log.info("User %s signed in from %s", user.username, client_ip)
    return user


def recent_sign_ins(limit: int = 20) -> list[LoginAttempt]:
    query = db.select(LoginAttempt).order_by(LoginAttempt.attempted_at.desc(), LoginAttempt.id.desc()).limit(limit)
    return list(db.session.scalars(query))


def _check_address(client_ip: str, now: datetime) -> None:
    failures = db.session.scalars(
        db.select(LoginAttempt.attempted_at)
        .where(
            LoginAttempt.ip_address == client_ip,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.attempted_at >= now - ADDRESS_WINDOW,
        )
        .order_by(LoginAttempt.attempted_at.desc())
        .limit(MAX_FAILED_PER_ADDRESS)
    ).all()
    if len(failures) >= MAX_FAILED_PER_ADDRESS:
        log.warning("Sign-ins from %s blocked after %d failures", client_ip, len(failures))
        # The address is free again once the oldest of those failures leaves the window
        raise TooManyAttemptsError(_minutes_left(_as_utc(failures[-1]) + ADDRESS_WINDOW, now))


def _log_attempt(client_ip: str, username: str, succeeded: bool, now: datetime) -> None:
    db.session.add(LoginAttempt(ip_address=client_ip, username=username.strip()[:50], succeeded=succeeded, attempted_at=now))
    # Keeps the log from growing forever
    db.session.execute(db.delete(LoginAttempt).where(LoginAttempt.attempted_at < now - LOGIN_LOG_RETENTION))
    db.session.commit()


def _check_credentials(username: str, password: str, now: datetime) -> User:
    user = find_user(username)
    if user is None or not user.is_active:
        # Hash anyway so unknown and known usernames take the same time to answer
        check_password_hash(_dummy_hash(), password)
        raise InvalidCredentialsError()

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
        raise UserError("username", f"El usuario '{normalize_username(username)}' no existe.")
    return user


def _clean_name(full_name: str) -> str:
    full_name = " ".join(full_name.split())
    if not 3 <= len(full_name) <= 100:
        raise UserError("full_name", "El nombre debe tener entre 3 y 100 caracteres.")
    return full_name


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise UserError("role", f"Rol desconocido. Usa uno de: {', '.join(ROLES)}.")


def _check_password(password: str, field: str = "password") -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(field, f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")


@cache
def _dummy_hash() -> str:
    return generate_password_hash("not-a-real-password")


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; they were stored in UTC
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _minutes_left(locked_until: datetime, now: datetime) -> int:
    return max(1, -(-int((_as_utc(locked_until) - now).total_seconds()) // 60))
