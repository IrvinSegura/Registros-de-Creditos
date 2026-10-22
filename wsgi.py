"""Entry point for `flask` CLI commands, WSGI servers and `python wsgi.py`."""

from dotenv import load_dotenv

# Load .env before the config classes read the environment
load_dotenv()

from app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    app.run()
