"""Sign-in and sign-out pages."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app.security import rotate_csrf_token
from app.services import user_service
from app.services.user_service import AccountLockedError, InvalidCredentialsError, TooManyAttemptsError

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_next_url())

    error, status, username = None, 200, ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        try:
            # Behind a trusted proxy, Waitress already puts the client's address here (see serve.py)
            client_ip = request.remote_addr or "unknown"
            user = user_service.authenticate(username, request.form.get("password", ""), client_ip)
        except (InvalidCredentialsError, AccountLockedError, TooManyAttemptsError) as failure:
            error, status = failure.message, failure.status.value
        else:
            login_user(user)
            # Sessions last PERMANENT_SESSION_LIFETIME instead of ending with the browser
            session.permanent = True
            rotate_csrf_token()
            return redirect(_next_url())

    return render_template("auth/login.html", error=error, username=username), status


@auth_bp.post("/logout")
def logout():
    logout_user()
    session.clear()
    flash("Cerraste sesión correctamente.", "success")
    return redirect(url_for("auth.login"))


def _next_url() -> str:
    # Only local paths: an absolute or protocol-relative URL would allow open redirects
    target = request.args.get("next", "")
    if target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("web.index")
