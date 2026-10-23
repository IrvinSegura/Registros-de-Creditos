"""`flask users ...` commands to manage accounts from the terminal."""

import click
from flask.cli import AppGroup

from app.auth.permissions import ROLE_LABELS, ROLES
from app.errors import DomainError
from app.services import user_service

users_cli = AppGroup("users", help="Manage user accounts.")

# Output is read by whoever runs the command, so it stays in Spanish like the rest of the interface
_ROLE_HELP = ", ".join(f"{role} ({label})" for role, label in ROLE_LABELS.items())


def _run(action):
    try:
        return action()
    except DomainError as error:
        raise click.ClickException(error.message) from None


@users_cli.command("create")
@click.argument("username")
@click.option("--name", "full_name", prompt="Nombre completo", help="Name shown in the interface.")
@click.option("--role", type=click.Choice(ROLES), default="analyst", show_default=True, help=_ROLE_HELP)
@click.password_option("--password", prompt="Contraseña", confirmation_prompt="Repite la contraseña")
def create_user(username: str, full_name: str, role: str, password: str) -> None:
    """Create an account."""
    user = _run(lambda: user_service.create_user(username, full_name, password, role))
    click.echo(f"Usuario '{user.username}' creado con el rol {ROLE_LABELS[user.role]}.")


@users_cli.command("list")
def list_users() -> None:
    """List every account."""
    users = user_service.list_users()
    if not users:
        click.echo("No hay usuarios. Crea el primero con: flask users create <usuario> --role admin")
        return
    for user in users:
        status = "activo" if user.is_active else "desactivado"
        click.echo(f"{user.username:<20} {user.full_name:<30} {ROLE_LABELS.get(user.role, user.role):<14} {status}")


@users_cli.command("set-password")
@click.argument("username")
@click.password_option("--password", prompt="Nueva contraseña", confirmation_prompt="Repite la contraseña")
def set_password(username: str, password: str) -> None:
    """Change an account's password; also unlocks it and ends its open sessions."""
    user = _run(lambda: user_service.set_password(username, password))
    click.echo(f"Contraseña de '{user.username}' actualizada. Sus sesiones abiertas se cerraron.")


@users_cli.command("end-sessions")
@click.argument("username")
def end_sessions(username: str) -> None:
    """Sign an account out of every browser without changing its password."""
    user = _run(lambda: user_service.end_sessions(username))
    click.echo(f"Se cerraron todas las sesiones de '{user.username}'.")


@users_cli.command("deactivate")
@click.argument("username")
def deactivate(username: str) -> None:
    """Block an account from signing in; its open sessions end on their next request."""
    user = _run(lambda: user_service.set_active(username, False))
    click.echo(f"Usuario '{user.username}' desactivado.")


@users_cli.command("activate")
@click.argument("username")
def activate(username: str) -> None:
    """Allow a deactivated account to sign in again."""
    user = _run(lambda: user_service.set_active(username, True))
    click.echo(f"Usuario '{user.username}' activado.")
