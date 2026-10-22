from datetime import date
from decimal import Decimal

from marshmallow import Schema, fields, pre_load, validate

# Letters (accents and ñ included) and spaces, starting with an uppercase letter
CLIENT_NAME_REGEX = r"^[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]*$"
MIN_ISSUE_DATE = date(2000, 1, 1)

# Validation messages are shown to end users, so they stay in Spanish
REQUIRED_MESSAGES = {"required": "Este campo es obligatorio.", "null": "Este campo no puede ser nulo."}


class CreditSchema(Schema):
    id = fields.Integer(dump_only=True)
    client_name = fields.String(
        required=True,
        error_messages={**REQUIRED_MESSAGES, "invalid": "Debe ser un texto."},
        validate=[
            validate.Length(min=3, max=100, error="El nombre debe tener entre {min} y {max} caracteres."),
            validate.Regexp(
                CLIENT_NAME_REGEX,
                error="El nombre debe empezar con mayúscula y contener solo letras y espacios.",
            ),
        ],
    )
    amount = fields.Decimal(
        required=True,
        places=2,
        as_string=True,
        error_messages={**REQUIRED_MESSAGES, "invalid": "Debe ser un número válido."},
        validate=validate.Range(
            min=Decimal("0.01"), max=Decimal("999999999999.99"), error="El monto debe ser mayor a 0."
        ),
    )
    interest_rate = fields.Decimal(
        required=True,
        places=2,
        as_string=True,
        error_messages={**REQUIRED_MESSAGES, "invalid": "Debe ser un número válido."},
        validate=validate.Range(
            min=0, min_inclusive=False, max=100, error="La tasa debe ser mayor a 0 y como máximo 100."
        ),
    )
    term_months = fields.Integer(
        required=True,
        strict=True,
        error_messages={**REQUIRED_MESSAGES, "invalid": "Debe ser un número entero."},
        validate=validate.Range(min=1, max=360, error="El plazo debe estar entre {min} y {max} meses."),
    )
    issue_date = fields.Date(
        required=True,
        error_messages={**REQUIRED_MESSAGES, "invalid": "Debe ser una fecha válida (AAAA-MM-DD)."},
        validate=validate.Range(min=MIN_ISSUE_DATE, error="La fecha debe ser posterior al 01/01/2000."),
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def normalize_client_name(self, data, **kwargs):
        # Trim and collapse repeated spaces so "  Ana   Paz " is stored as "Ana Paz"
        if isinstance(data, dict) and isinstance(data.get("client_name"), str):
            data = {**data, "client_name": " ".join(data["client_name"].split())}
        return data


class CreditQuerySchema(Schema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=10, validate=validate.Range(min=1, max=100))
    client_name = fields.String(metadata={"description": "Case-insensitive 'contains' filter on the client name."})


class PaginationSchema(Schema):
    page = fields.Integer()
    per_page = fields.Integer()
    total = fields.Integer()
    pages = fields.Integer()


class CreditPageSchema(Schema):
    items = fields.List(fields.Nested(CreditSchema))
    meta = fields.Nested(PaginationSchema)


class MonthlyTotalSchema(Schema):
    year = fields.Integer()
    month = fields.Integer()
    credits = fields.Integer()
    total_amount = fields.Decimal(places=2, as_string=True)


class TermRangeSchema(Schema):
    range = fields.String(metadata={"description": "Term bucket in months: 1-12, 13-24, 25-36 or 37+."})
    credits = fields.Integer()


class CreditSummarySchema(Schema):
    total_credits = fields.Integer()
    total_amount = fields.Decimal(places=2, as_string=True)
    average_amount = fields.Decimal(places=2, as_string=True)
    average_interest_rate = fields.Decimal(places=2, as_string=True)
    average_term_months = fields.Decimal(places=1, as_string=True)
    monthly = fields.List(fields.Nested(MonthlyTotalSchema))
    by_term = fields.List(fields.Nested(TermRangeSchema))
