"""REST endpoints for user accounts: administration (admin role) and each user's own password."""

from flask import session
from flask.views import MethodView
from flask_login import current_user, login_user
from flask_smorest import Blueprint

from app.auth.permissions import MANAGE_USERS, require_permission
from app.schemas.user import NewUserSchema, PasswordChangeSchema, PasswordResetSchema, UserSchema, UserUpdateSchema
from app.services import user_service

blp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/v1",
    description="User accounts. Managing other accounts requires the admin role; any user can change their own password.",
)


def _keep_signed_in(user) -> None:
    # A new password ends every session, this one included; sign it in again with the new session token
    login_user(user)
    session.permanent = True


@blp.route("/users")
class UsersResource(MethodView):
    @require_permission(MANAGE_USERS)
    @blp.response(200, UserSchema(many=True))
    @blp.alt_response(403, response="FORBIDDEN")
    def get(self):
        """List every account."""
        return user_service.list_users()

    @require_permission(MANAGE_USERS)
    @blp.arguments(NewUserSchema)
    @blp.response(201, UserSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    def post(self, data):
        """Create an account."""
        return user_service.create_user(data["username"], data["full_name"], data["password"], data["role"])


@blp.route("/users/<int:user_id>")
class UserResource(MethodView):
    @require_permission(MANAGE_USERS)
    @blp.arguments(UserUpdateSchema)
    @blp.response(200, UserSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def put(self, data, user_id):
        """Change an account's name, role or whether it can sign in. Deactivating it ends its sessions."""
        return user_service.update_user(user_id, data["full_name"], data["role"], data["is_active"], current_user)


@blp.route("/users/<int:user_id>/password")
class UserPasswordResource(MethodView):
    @require_permission(MANAGE_USERS)
    @blp.arguments(PasswordResetSchema)
    @blp.response(204)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def post(self, data, user_id):
        """Set a new password for an account; also unlocks it and ends its sessions."""
        user = user_service.reset_password(user_id, data["password"], current_user)
        if user.id == current_user.id:
            _keep_signed_in(user)


@blp.route("/users/<int:user_id>/end-sessions")
class UserSessionsResource(MethodView):
    @require_permission(MANAGE_USERS)
    @blp.response(204)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def post(self, user_id):
        """Sign an account out of every browser."""
        user = user_service.end_sessions(user_service.require_user_by_id(user_id).username)
        if user.id == current_user.id:
            _keep_signed_in(user)


@blp.route("/account/password")
class AccountPasswordResource(MethodView):
    @blp.arguments(PasswordChangeSchema)
    @blp.response(204)
    def post(self, data):
        """Change your own password. Your other sessions end; this one stays open."""
        # The proxy itself cannot be signed in again, only the user object behind it
        user = current_user._get_current_object()
        user_service.change_own_password(user, data["current_password"], data["new_password"])
        _keep_signed_in(user)
