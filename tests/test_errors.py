import pytest
from werkzeug.exceptions import InternalServerError

URL = "/api/v1/credits"


def test_missing_pages_show_an_html_page(client):
    response = client.get("/no-existe")

    assert response.status_code == 404
    assert response.mimetype == "text/html"
    html = response.get_data(as_text=True)
    assert "No encontramos esta página" in html
    assert "Volver al inicio" in html


def test_api_errors_stay_json(client):
    response = client.get(f"{URL}/999")

    assert response.status_code == 404
    assert response.mimetype == "application/json"
    assert client.get("/api/v1/no-existe").get_json() == {"code": 404, "status": "Not Found"}


@pytest.fixture
def failing_page(app):
    # Routes are added before the signed-in client makes its first request, so it goes first in the tests;
    # exceptions are handled as in production instead of being raised to the test
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def crash():
        raise RuntimeError("boom")

    app.add_url_rule("/crash", "crash", crash)
    app.add_url_rule("/api/v1/crash", "api_crash", crash)


def test_unexpected_errors_show_a_friendly_page(failing_page, client):
    response = client.get("/crash")

    assert response.status_code == InternalServerError.code
    assert "Algo salió mal" in response.get_data(as_text=True)
    assert "boom" not in response.get_data(as_text=True)


def test_unexpected_api_errors_answer_json_without_details(failing_page, client):
    response = client.get("/api/v1/crash")

    assert response.status_code == 500
    assert response.get_json() == {"code": 500, "status": "Internal Server Error"}
