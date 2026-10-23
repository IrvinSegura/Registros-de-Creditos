from marshmallow import Schema, fields, validate

from app.auth.permissions import ROLE_LABELS, ROLES
from app.schemas.credit import REQUIRED_MESSAGES

# Length and format rules live in user_service, which the CLI shares; these only check types and presence
TEXT_MESSAGES = {**REQUIRED_MESSAGES, "invalid": "Debe ser un texto."}


class UserSchema(Schema):
    id = fields.Integer(dump_only=True)
    username = fields.String(required=True, error_messages=TEXT_MESSAGES)
    full_name = fields.String(required=True, error_messages=TEXT_MESSAGES)
    role = fields.String(
        required=True,
        validate=validate.OneOf(ROLES, error="Rol desconocido."),
        metadata={"description": "admin, analyst or viewer."},
    )
    role_label = fields.Function(lambda user: ROLE_LABELS.get(user.role, user.role), dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    locked = fields.Function(
        lambda user: user.locked_until is not None,
        dump_only=True,
        metadata={"description": "Locked for a while after repeated failed sign-ins."},
    )
    last_login_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class NewUserSchema(UserSchema):
    password = fields.String(required=True, load_only=True, error_messages=TEXT_MESSAGES)


class UserUpdateSchema(Schema):
    full_name = fields.String(required=True, error_messages=TEXT_MESSAGES)
    role = fields.String(required=True, validate=validate.OneOf(ROLES, error="Rol desconocido."))
    is_active = fields.Boolean(required=True, error_messages=REQUIRED_MESSAGES)


class PasswordResetSchema(Schema):
    password = fields.String(required=True, load_only=True, error_messages=TEXT_MESSAGES)


class PasswordChangeSchema(Schema):
    current_password = fields.String(required=True, load_only=True, error_messages=TEXT_MESSAGES)
    new_password = fields.String(required=True, load_only=True, error_messages=TEXT_MESSAGES)
