"""HTTP security: headers with a per-request CSP nonce, and CSRF tokens for state-changing requests."""

import secrets
from http import HTTPStatus

from flask import Flask, Response, flash, g, redirect, request, session, url_for

from app.errors import DomainError

CDN = "https://cdn.jsdelivr.net"
FONTS_CSS = "https://fonts.googleapis.com"
FONTS_FILES = "https://fonts.gstatic.com"
DOCS_PATH = "/api/docs"
API_PATH = "/api/"

CSRF_SESSION_KEY = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FIELD = "csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _app_policy(nonce: str) -> str:
    return "; ".join(
        (
            "default-src 'self'",
            f"script-src 'self' {CDN} 'nonce-{nonce}'",
            f"style-src 'self' {CDN} {FONTS_CSS}",
            f"font-src 'self' {CDN} {FONTS_FILES}",
            # Bootstrap draws some icons (validation, close button) as data: SVGs
            "img-src 'self' data:",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        )
    )


# Swagger UI renders with inline scripts and styles, so its page gets a looser policy
DOCS_POLICY = "; ".join(
    (
        "default-src 'self'",
        f"script-src 'self' 'unsafe-inline' {CDN}",
        f"style-src 'self' 'unsafe-inline' {CDN}",
        "img-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
    )
)


def register_security_headers(app: Flask) -> None:
    @app.before_request
    def create_nonce() -> None:
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_nonce() -> dict[str, str]:
        return {"csp_nonce": g.get("csp_nonce", "")}

    @app.after_request
    def add_headers(response: Response) -> Response:
        policy = DOCS_POLICY if request.path.startswith(DOCS_PATH) else _app_policy(g.get("csp_nonce", ""))
        response.headers.setdefault("Content-Security-Policy", policy)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if app.config["ENV_NAME"] == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class CsrfError(DomainError):
    status = HTTPStatus.FORBIDDEN

    def __init__(self):
        super().__init__("La página expiró. Recárgala e intenta de nuevo.")


def csrf_token() -> str:
    """The session's CSRF token, created on first use."""
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def rotate_csrf_token() -> str:
    # Called on sign-in so a token seen before authenticating is no longer valid
    session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def register_csrf_protection(app: Flask) -> None:
    @app.context_processor
    def inject_csrf_token() -> dict:
        return {"csrf_token": csrf_token}

    @app.before_request
    def check_csrf_token():
        if request.method in SAFE_METHODS:
            return None
        sent = request.headers.get(CSRF_HEADER) or request.form.get(CSRF_FIELD, "")
        expected = session.get(CSRF_SESSION_KEY, "")
        if expected and secrets.compare_digest(sent.encode(), expected.encode()):
            return None
        if request.path.startswith(API_PATH):
            raise CsrfError()
        # Page forms (sign-in, sign-out) go back to the sign-in page with the reason
        flash(CsrfError().message, "error")
        return redirect(url_for("auth.login"))
