import pytest

from app.cli import users_cli
from app.services import user_service
from app.extensions import db
from app.models import LoginAttempt
from app.services.user_service import ADDRESS_WINDOW, MAX_FAILED_LOGINS, MAX_FAILED_PER_ADDRESS, UserError
from tests.conftest import PASSWORD, sign_in

URL = "/api/v1/credits"


# ---------- Guard ----------

def test_pages_redirect_anonymous_users_to_sign_in(anonymous_client):
    response = anonymous_client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/"


def test_api_answers_401_to_anonymous_users(anonymous_client):
    response = anonymous_client.get(URL)

    assert response.status_code == 401
    assert response.get_json()["message"] == "Tu sesión expiró. Inicia sesión de nuevo."


def test_api_docs_require_sign_in(anonymous_client):
    assert anonymous_client.get("/api/docs").status_code == 302
    assert anonymous_client.get("/api/openapi.json").status_code == 302


def test_sign_in_page_and_static_files_are_public(anonymous_client):
    assert anonymous_client.get("/login").status_code == 200
    assert anonymous_client.get("/static/css/base.css").status_code == 200


# ---------- Sign-in ----------

def test_sign_in_redirects_to_the_requested_page(app, make_user):
    make_user()
    client = app.test_client()
    client.get("/login")
    with client.session_transaction() as session:
        token = session["csrf_token"]

    response = client.post(
        "/login?next=/%23/creditos", data={"username": "ADMIN ", "password": PASSWORD, "csrf_token": token}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/#/creditos"
    assert client.get(URL).status_code == 200


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_sign_in_ignores_external_redirects(app, make_user, target):
    make_user()
    client = app.test_client()
    client.get("/login")
    with client.session_transaction() as session:
        token = session["csrf_token"]

    response = client.post(f"/login?next={target}", data={"username": "admin", "password": PASSWORD, "csrf_token": token})

    assert response.headers["Location"] == "/"


def test_wrong_password_keeps_the_username_and_explains(app, make_user):
    make_user()
    client = app.test_client()

    response = sign_in(client, "admin", "wrong-password")

    assert response.status_code == 401
    html = response.get_data(as_text=True)
    assert "Usuario o contraseña incorrectos." in html
    assert 'value="admin"' in html


def test_unknown_and_inactive_users_get_the_same_answer(app, make_user):
    make_user()
    user_service.set_active("admin", False)

    unknown = sign_in(app.test_client(), "nobody")
    inactive = sign_in(app.test_client(), "admin")

    assert unknown.status_code == inactive.status_code == 401


def test_account_locks_after_repeated_failures(app, make_user):
    make_user()
    for _ in range(MAX_FAILED_LOGINS - 1):
        assert sign_in(app.test_client(), "admin", "wrong-password").status_code == 401

    locked = sign_in(app.test_client(), "admin", "wrong-password")
    still_locked = sign_in(app.test_client(), "admin")

    assert locked.status_code == 429
    assert "se bloqueó" in locked.get_data(as_text=True)
    assert still_locked.status_code == 429


def test_new_password_unlocks_the_account(app, make_user):
    make_user()
    for _ in range(MAX_FAILED_LOGINS):
        sign_in(app.test_client(), "admin", "wrong-password")

    user_service.set_password("admin", "another-secret-1")

    assert sign_in(app.test_client(), "admin", "another-secret-1").status_code == 302


def test_successful_sign_in_resets_the_failure_count(app, make_user):
    make_user()
    sign_in(app.test_client(), "admin", "wrong-password")

    sign_in(app.test_client(), "admin")

    user = user_service.find_user("admin")
    assert user.failed_logins == 0
    assert user.last_login_at is not None


def client_from(app, address):
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = address
    return client


def test_address_is_blocked_after_failures_on_any_usernames(app, make_user):
    make_user()
    attacker = client_from(app, "203.0.113.7")
    for number in range(MAX_FAILED_PER_ADDRESS):
        assert sign_in(attacker, f"ghost{number}", "wrong-password").status_code == 401

    blocked = sign_in(attacker, "admin")

    assert blocked.status_code == 429
    assert "Demasiados intentos fallidos desde esta conexión" in blocked.get_data(as_text=True)
    # Other addresses, and the account itself, are not affected
    assert sign_in(client_from(app, "198.51.100.1"), "admin").status_code == 302


def test_address_block_ends_with_the_window(app, make_user):
    make_user()
    attacker = client_from(app, "203.0.113.7")
    for number in range(MAX_FAILED_PER_ADDRESS):
        sign_in(attacker, f"ghost{number}", "wrong-password")

    # Move the failures back in time, past the window
    for attempt in db.session.scalars(db.select(LoginAttempt)):
        attempt.attempted_at = attempt.attempted_at - ADDRESS_WINDOW
    db.session.commit()

    assert sign_in(attacker, "admin").status_code == 302


def test_every_attempt_is_logged(app, make_user):
    make_user()
    sign_in(client_from(app, "203.0.113.7"), "admin", "wrong-password")
    sign_in(client_from(app, "203.0.113.8"), "admin")

    attempts = user_service.recent_sign_ins()

    assert [(a.ip_address, a.username, a.succeeded) for a in attempts] == [
        ("203.0.113.8", "admin", True),
        ("203.0.113.7", "admin", False),
    ]
    listed = app.test_cli_runner().invoke(users_cli, ["sign-ins"])
    assert "203.0.113.7" in listed.output
    assert "fallido" in listed.output


def test_session_cookie_is_http_only_and_same_site(app, make_user):
    make_user()
    response = sign_in(app.test_client(), "admin")

    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


# ---------- Sign-out and session end ----------

def test_sign_out_ends_the_session(client):
    with client.session_transaction() as session:
        token = session["csrf_token"]

    response = client.post("/logout", data={"csrf_token": token})

    assert response.headers["Location"] == "/login"
    assert client.get(URL).status_code == 401


def test_deactivated_users_lose_their_open_session(client):
    user_service.set_active("admin", False)

    assert client.get(URL).status_code == 401


def test_changing_the_password_ends_open_sessions(client):
    user_service.set_password("admin", "another-secret-1")

    assert client.get(URL).status_code == 401


def test_password_change_only_signs_out_that_user(client_as):
    admin = client_as("admin")
    viewer = client_as("viewer")

    user_service.set_password("viewer", "another-secret-1")

    assert admin.get(URL).status_code == 200
    assert viewer.get(URL).status_code == 401


def test_end_sessions_command_signs_the_user_out(app, client):
    result = app.test_cli_runner().invoke(users_cli, ["end-sessions", "admin"])

    assert result.exit_code == 0, result.output
    assert "Se cerraron todas las sesiones de 'admin'." in result.output
    assert client.get(URL).status_code == 401
    assert sign_in(app.test_client(), "admin").status_code == 302


def test_sessions_that_hold_the_user_id_are_rejected(app, make_user):
    # Sessions opened before the session tokens existed stored the numeric id
    user = make_user()
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True

    assert client.get(URL).status_code == 401


# ---------- CSRF ----------

def test_api_rejects_writes_without_the_csrf_token(client, valid_credit):
    client.environ_base.pop("HTTP_X_CSRF_TOKEN")

    response = client.post(URL, json=valid_credit)

    assert response.status_code == 403
    assert response.get_json()["message"] == "La página expiró. Recárgala e intenta de nuevo."


def test_api_rejects_a_wrong_csrf_token(client, valid_credit):
    response = client.post(URL, json=valid_credit, headers={"X-CSRF-Token": "forged"})

    assert response.status_code == 403


def test_sign_in_form_without_csrf_token_goes_back_with_a_message(app, make_user):
    make_user()
    client = app.test_client()

    response = client.post("/login", data={"username": "admin", "password": PASSWORD}, follow_redirects=True)

    assert "La página expiró" in response.get_data(as_text=True)
    assert client.get(URL).status_code == 401


# ---------- Roles ----------

def test_viewer_can_read_but_not_write(client_as, create_credit, valid_credit):
    credit = create_credit()
    viewer = client_as("viewer")

    assert viewer.get(URL).status_code == 200
    assert viewer.get(f"{URL}/{credit['id']}/history").status_code == 200
    assert viewer.get(f"{URL}/export").status_code == 200
    assert viewer.post(URL, json=valid_credit).status_code == 403
    assert viewer.put(f"{URL}/{credit['id']}", json=valid_credit).status_code == 403
    assert viewer.delete(f"{URL}/{credit['id']}").status_code == 403


def test_permission_is_checked_before_the_body(client_as):
    response = client_as("viewer").post(URL, json={})

    assert response.status_code == 403
    assert response.get_json()["message"] == "No tienes permiso para realizar esta acción."


def test_analyst_can_create_and_edit_but_not_delete(client_as, valid_credit):
    analyst = client_as("analyst")

    created = analyst.post(URL, json=valid_credit)
    updated = analyst.put(f"{URL}/{created.get_json()['id']}", json={**valid_credit, "term_months": 36})
    deleted = analyst.delete(f"{URL}/{created.get_json()['id']}")

    assert (created.status_code, updated.status_code, deleted.status_code) == (201, 200, 403)


def test_page_only_renders_what_the_role_can_use(client_as):
    viewer_html = client_as("viewer").get("/").get_data(as_text=True)
    admin_html = client_as("admin").get("/").get_data(as_text=True)

    assert 'data-permissions="credits:view"' in viewer_html
    for marker in ('data-view="register"', 'id="topbar-new"', 'id="edit-credit-modal"', 'id="detail-delete"'):
        assert marker not in viewer_html
        assert marker in admin_html
    assert "Usuario Viewer" in viewer_html
    assert "Consulta" in viewer_html


def test_history_records_who_made_each_change(client, create_credit, valid_credit):
    credit = create_credit()
    client.put(f"{URL}/{credit['id']}", json={**valid_credit, "amount": "20000"})

    history = client.get(f"{URL}/{credit['id']}/history").get_json()

    assert [entry["changed_by"] for entry in history] == ["Usuario Admin", "Usuario Admin"]


# ---------- Accounts ----------

@pytest.mark.parametrize(
    ("username", "full_name", "password", "role", "message"),
    [
        ("a", "Ana Paz", PASSWORD, "admin", "El usuario debe tener"),
        ("ana paz", "Ana Paz", PASSWORD, "admin", "El usuario debe tener"),
        ("ana", "A", PASSWORD, "admin", "El nombre debe tener"),
        ("ana", "Ana Paz", "short", "admin", "al menos 10 caracteres"),
        ("ana", "Ana Paz", PASSWORD, "owner", "Rol desconocido"),
    ],
)
def test_create_user_validates_its_data(app, username, full_name, password, role, message):
    with pytest.raises(UserError, match=message):
        user_service.create_user(username, full_name, password, role)


def test_usernames_are_unique_regardless_of_case(make_user):
    make_user(username="ana")

    with pytest.raises(UserError, match="ya existe"):
        make_user(username="ANA")


def test_cli_creates_and_lists_users(app):
    runner = app.test_cli_runner()

    created = runner.invoke(users_cli, ["create", "luis", "--name", "Luis Vega", "--role", "viewer"],
                            input=f"{PASSWORD}\n{PASSWORD}\n")
    listed = runner.invoke(users_cli, ["list"])
    duplicate = runner.invoke(users_cli, ["create", "luis", "--name", "Luis Vega"], input=f"{PASSWORD}\n{PASSWORD}\n")

    assert created.exit_code == 0, created.output
    assert "Usuario 'luis' creado con el rol Consulta." in created.output
    assert "Luis Vega" in listed.output
    assert duplicate.exit_code == 1
    assert "ya existe" in duplicate.output
