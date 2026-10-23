import pytest

from tests.conftest import PASSWORD, sign_in

URL = "/api/v1/users"
NEW_PASSWORD = "another-secret-1"


def new_user(**changes):
    return {"username": "luis", "full_name": "Luis Vega", "role": "viewer", "password": PASSWORD, **changes}


def test_admin_lists_and_creates_users(client):
    created = client.post(URL, json=new_user())

    assert created.status_code == 201
    body = created.get_json()
    assert (body["username"], body["role_label"], body["is_active"]) == ("luis", "Consulta", True)
    assert "password" not in body
    assert [user["username"] for user in client.get(URL).get_json()] == ["admin", "luis"]


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"username": "a"}, "username"),
        ({"username": "admin"}, "username"),
        ({"full_name": "Lu"}, "full_name"),
        ({"password": "short"}, "password"),
        ({"role": "owner"}, "role"),
    ],
)
def test_new_users_are_validated_per_field(client, changes, field):
    response = client.post(URL, json=new_user(**changes))

    assert response.status_code == 422
    assert field in response.get_json()["errors"]["json"]


def test_only_admins_manage_users(client_as):
    analyst = client_as("analyst")

    assert analyst.get(URL).status_code == 403
    assert analyst.post(URL, json=new_user()).status_code == 403


def test_admin_changes_role_and_deactivates(app, client, make_user):
    user = make_user(username="luis", role="analyst", full_name="Luis Vega")
    luis = app.test_client()
    sign_in(luis, "luis")

    response = client.put(f"{URL}/{user.id}", json={"full_name": "Luis Vega Paz", "role": "viewer", "is_active": False})

    assert response.status_code == 200
    assert response.get_json()["role"] == "viewer"
    assert luis.get("/api/v1/credits").status_code == 401
    assert sign_in(app.test_client(), "luis").status_code == 401


def test_admin_cannot_lock_themselves_out(client):
    me = client.get(URL).get_json()[0]

    demoted = client.put(f"{URL}/{me['id']}", json={"full_name": me["full_name"], "role": "viewer", "is_active": True})
    deactivated = client.put(f"{URL}/{me['id']}", json={"full_name": me["full_name"], "role": "admin", "is_active": False})

    assert demoted.status_code == deactivated.status_code == 422
    assert "role" in demoted.get_json()["errors"]["json"]
    assert "is_active" in deactivated.get_json()["errors"]["json"]


def test_admin_resets_a_password(app, client, make_user):
    user = make_user(username="luis", role="viewer", full_name="Luis Vega")

    response = client.post(f"{URL}/{user.id}/password", json={"password": NEW_PASSWORD})

    assert response.status_code == 204
    assert sign_in(app.test_client(), "luis", password=NEW_PASSWORD).status_code == 302


def test_admin_ends_another_users_sessions(app, client, make_user):
    user = make_user(username="luis", role="viewer", full_name="Luis Vega")
    luis = app.test_client()
    sign_in(luis, "luis")

    assert client.post(f"{URL}/{user.id}/end-sessions").status_code == 204
    assert luis.get("/api/v1/credits").status_code == 401
    assert client.get("/api/v1/credits").status_code == 200


def test_missing_user_is_not_found(client):
    assert client.put(f"{URL}/999", json={"full_name": "Luis Vega", "role": "viewer", "is_active": True}).status_code == 404


# ---------- Own password ----------

def test_any_user_changes_their_own_password_and_stays_signed_in(app, client_as):
    viewer = client_as("viewer")
    other_browser = app.test_client()
    sign_in(other_browser, "viewer")

    response = viewer.post("/api/v1/account/password", json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})

    assert response.status_code == 204
    assert viewer.get("/api/v1/credits").status_code == 200
    assert other_browser.get("/api/v1/credits").status_code == 401
    assert sign_in(app.test_client(), "viewer", password=NEW_PASSWORD).status_code == 302


@pytest.mark.parametrize(
    ("current", "new", "field"),
    [
        ("wrong-password", NEW_PASSWORD, "current_password"),
        (PASSWORD, "short", "new_password"),
        (PASSWORD, PASSWORD, "new_password"),
    ],
)
def test_own_password_change_is_validated(client, current, new, field):
    response = client.post("/api/v1/account/password", json={"current_password": current, "new_password": new})

    assert response.status_code == 422
    assert field in response.get_json()["errors"]["json"]
