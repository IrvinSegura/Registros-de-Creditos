import re

from app import create_app
from app.config import DevelopmentConfig


def test_pages_send_security_headers(client):
    response = client.get("/")

    policy = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "'unsafe-inline'" not in policy
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_inline_script_uses_the_request_nonce(client):
    response = client.get("/")

    nonce = re.search(r"'nonce-([^']+)'", response.headers["Content-Security-Policy"]).group(1)
    assert f'nonce="{nonce}"' in response.get_data(as_text=True)
    assert nonce not in client.get("/").headers["Content-Security-Policy"]


def test_cdn_assets_carry_integrity_hashes(client):
    html = client.get("/").get_data(as_text=True)

    cdn_tags = re.findall(r"<(?:script|link)[^>]+https://cdn\.jsdelivr\.net[^>]*>", html)
    assert cdn_tags
    assert all('integrity="sha384-' in tag and 'crossorigin="anonymous"' in tag for tag in cdn_tags)


def test_api_docs_get_their_own_policy(client):
    policy = client.get("/api/docs").headers["Content-Security-Policy"]

    assert "'unsafe-inline'" in policy


def test_pages_and_api_answers_are_never_stored(client):
    assert client.get("/").headers["Cache-Control"] == "no-store"
    assert client.get("/api/v1/credits").headers["Cache-Control"] == "no-store"
    assert client.get("/login").headers["Cache-Control"] == "no-store"


def test_static_files_are_revalidated_instead_of_stored(client):
    response = client.get("/static/css/base.css")

    assert response.headers["Cache-Control"] == "no-cache"
    assert response.headers["ETag"]


def test_development_reloads_edited_templates():
    app = create_app(DevelopmentConfig)
    # What `flask run` does when --debug is not given
    app.debug = False

    assert app.jinja_env.auto_reload is True
