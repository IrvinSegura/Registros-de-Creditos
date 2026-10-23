"""Roles and the actions each one may perform."""

from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from typing import Any

from flask_login import current_user

from app.errors import DomainError

VIEW_CREDITS = "credits:view"
CREATE_CREDITS = "credits:create"
UPDATE_CREDITS = "credits:update"
DELETE_CREDITS = "credits:delete"

ADMIN = "admin"
ANALYST = "analyst"
VIEWER = "viewer"

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ADMIN: frozenset({VIEW_CREDITS, CREATE_CREDITS, UPDATE_CREDITS, DELETE_CREDITS}),
    ANALYST: frozenset({VIEW_CREDITS, CREATE_CREDITS, UPDATE_CREDITS}),
    VIEWER: frozenset({VIEW_CREDITS}),
}
ROLES = tuple(ROLE_PERMISSIONS)

# Role names are shown in the interface, so they stay in Spanish
ROLE_LABELS = {ADMIN: "Administrador", ANALYST: "Analista", VIEWER: "Consulta"}


class UnauthorizedError(DomainError):
    status = HTTPStatus.UNAUTHORIZED

    def __init__(self):
        super().__init__("Tu sesión expiró. Inicia sesión de nuevo.")


class ForbiddenError(DomainError):
    status = HTTPStatus.FORBIDDEN

    def __init__(self):
        super().__init__("No tienes permiso para realizar esta acción.")


def permissions_of(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def can(permission: str) -> bool:
    return current_user.is_authenticated and permission in permissions_of(current_user.role)


def require_permission(permission: str) -> Callable:
    """Rejects the request with 403 unless the signed-in user's role grants the permission."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not can(permission):
                raise ForbiddenError()
            return view(*args, **kwargs)

        return wrapper

    return decorator
