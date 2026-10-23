"""Sign-in: session handling, the sign-in pages and the guard that protects every other route."""

from flask import Flask, redirect, request, url_for
from flask_login import current_user

from app.auth.permissions import ROLE_LABELS, UnauthorizedError, can, permissions_of
from app.auth.views import auth_bp
from app.extensions import login_manager
from app.services import user_service

# Endpoints reachable without signing in
PUBLIC_ENDPOINTS = frozenset({"auth.login", "static"})
# JSON endpoints answer 401; everything else (pages, API docs) redirects to the sign-in page
JSON_API_PATH = "/api/v"


def register_auth(app: Flask) -> None:
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id: str):
        user = user_service.get_user(int(user_id))
        # A deactivated account loses its open sessions on the next request
        return user if user and user.is_active else None

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or current_user.is_authenticated:
            return None
        if request.path.startswith(JSON_API_PATH):
            raise UnauthorizedError()
        target = request.full_path if request.query_string else request.path
        return redirect(url_for("auth.login", next=target))

    @app.context_processor
    def inject_permissions() -> dict:
        role = current_user.role if current_user.is_authenticated else ""
        return {"can": can, "permissions": sorted(permissions_of(role)), "role_label": ROLE_LABELS.get(role, "")}
