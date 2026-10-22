"""HTTP security headers, including a Content Security Policy with a per-request nonce."""

import secrets

from flask import Flask, Response, g, request

CDN = "https://cdn.jsdelivr.net"
FONTS_CSS = "https://fonts.googleapis.com"
FONTS_FILES = "https://fonts.gstatic.com"
DOCS_PATH = "/api/docs"


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
