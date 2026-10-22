"""Domain errors and their translation into JSON HTTP responses."""

from http import HTTPStatus

from flask import Flask


class DomainError(Exception):
    """Base class for business errors raised by the service layer."""

    status = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status = HTTPStatus.NOT_FOUND


def register_error_handlers(app: Flask) -> None:
    # HTTP errors (404, 422, 500...) are already rendered as JSON by flask-smorest;
    # domain errors reuse the same payload shape: {code, status, message}
    @app.errorhandler(DomainError)
    def handle_domain_error(error: DomainError):
        payload = {"code": error.status.value, "status": error.status.phrase, "message": error.message}
        return payload, error.status.value
