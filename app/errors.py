"""Domain errors and their translation into JSON HTTP responses."""

from http import HTTPStatus

from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

from app.extensions import api

API_PATH = "/api/"

# What an error page tells the user; codes not listed show the generic message
PAGE_MESSAGES = {
    HTTPStatus.NOT_FOUND: ("No encontramos esta página", "La dirección no existe o se movió."),
    HTTPStatus.METHOD_NOT_ALLOWED: ("Acción no permitida", "Esta página no admite esa acción."),
    HTTPStatus.INTERNAL_SERVER_ERROR: (
        "Algo salió mal",
        "Ocurrió un error inesperado. Intenta de nuevo en unos minutos.",
    ),
}
GENERIC_MESSAGE = ("No se pudo mostrar la página", "Intenta de nuevo o vuelve al inicio.")


class DomainError(Exception):
    """Base class for business errors raised by the service layer."""

    status = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status = HTTPStatus.NOT_FOUND


class ConflictError(DomainError):
    """The request is valid, but the resource's current state does not allow it."""

    status = HTTPStatus.CONFLICT


class FieldError(DomainError):
    """A business rule broken by one field, reported like a validation error so forms show it next to the field."""

    status = HTTPStatus.UNPROCESSABLE_ENTITY

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def register_error_handlers(app: Flask) -> None:
    # Replaces flask-smorest's HTTP error handler (registered earlier, in api.init_app):
    # the API keeps its JSON payloads and pages get an HTML page instead of raw JSON.
    # Unhandled exceptions arrive here too, as a 500.
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        if request.path.startswith(API_PATH):
            return api.handle_http_exception(error)
        title, text = PAGE_MESSAGES.get(error.code, GENERIC_MESSAGE)
        return render_template("errors/error.html", code=error.code, title=title, text=text), error.code

    # Domain errors reuse the API payload shape: {code, status, message}, plus errors.json for field errors
    @app.errorhandler(DomainError)
    def handle_domain_error(error: DomainError):
        payload = {"code": error.status.value, "status": error.status.phrase, "message": error.message}
        if isinstance(error, FieldError):
            payload["errors"] = {"json": {error.field: [error.message]}}
        return payload, error.status.value
