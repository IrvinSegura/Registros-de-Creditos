"""Production entry point: serves the app with Waitress, a WSGI server that also runs on Windows.

Run it with `python serve.py` after setting APP_ENV=production and SECRET_KEY (see .env.example).
In production the session cookie is HTTPS-only, so the app is meant to sit behind a reverse proxy
that terminates TLS (IIS, nginx, Caddy...); TRUSTED_PROXY tells Waitress to trust that proxy's
X-Forwarded-* headers, so the app sees the original client address and the https scheme.
It also copies the SQLite database at start-up and every BACKUP_INTERVAL_HOURS (see .env.example).
"""

import os

from waitress import serve

from wsgi import app  # also loads .env, so it must be imported before anything else from app/

from app.services.backup_service import schedule_backups  # noqa: E402  isort:skip


def main() -> None:
    options = {
        "host": os.getenv("HOST", "127.0.0.1"),
        "port": int(os.getenv("PORT", "8000")),
        "threads": int(os.getenv("THREADS", "8")),
    }
    trusted_proxy = os.getenv("TRUSTED_PROXY", "")
    if trusted_proxy:
        options.update(
            trusted_proxy=trusted_proxy,
            trusted_proxy_count=1,
            trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"},
            clear_untrusted_proxy_headers=True,
        )
    schedule_backups(app)
    serve(app, **options)


if __name__ == "__main__":
    main()
