from datetime import date
from decimal import Decimal

from marshmallow import Schema, ValidationError, fields, pre_load, validate, validates_schema

CENT = Decimal("0.01")

# Letters (accents and ñ included) and spaces, starting with an uppercase letter
CLIENT_NAME_REGEX = r"^[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]*$"
MIN_ISSUE_DATE = date(2000, 1, 1)
MAX_AMOUNT = Decimal("999999999999.99")
SORT_FIELDS = ("id", "client_name", "amount", "interest_rate", "term_months", "issue_date", "created_at")

# Validation messages are shown to end users, so they stay in Spanish
REQUIRED_MESSAGES = {"required": "Este campo es obligatorio.", "null": "Este campo no puede ser nulo."}
NUMBER_MESSAGES = {**REQUIRED_MESSAGES, "invalid": "Debe ser un número válido."}
DATE_MESSAGES = {**REQUIRED_MESSAGES, "invalid": "Debe ser una fecha válida (AAAA-MM-DD)."}


class CentsDecimal(fields.Decimal):
    """Decimal with at most two places: extra places are rejected instead of silently rounded."""

    default_error_messages = {"places": "Usa como máximo 2 decimales."}

    def __init__(self, **kwargs):
        super().__init__(places=2, as_string=True, **kwargs)

    def _format_num(self, value):
        number = Decimal(str(value))
        # 1.500 is fine, 1.505 is not
        if number.is_finite() and number != number.quantize(CENT):
            raise self.make_error("places")
        return super()._format_num(value)


def not_in_future(value: date) -> None:
    # Checked on each request, so "today" never goes stale
    if value > date.today():
        raise ValidationError("La fecha no puede ser posterior a hoy.")


# Field factories shared by the credit payload and the quote query
def amount_field(**kwargs) -> CentsDecimal:
    return CentsDecimal(
        error_messages=NUMBER_MESSAGES,
        validate=validate.Range(
            min=CENT, max=MAX_AMOUNT, error="El monto debe ser mayor a 0 y como máximo 999,999,999,999.99."
        ),
        **kwargs,
    )


def interest_rate_field(**kwargs) -> CentsDecimal:
    return CentsDecimal(
        error_messages=NUMBER_MESSAGES,
        validate=validate.Range(min=0, min_inclusive=False, max=100, error="La tasa debe ser mayor a 0 y como máximo 100."),
        metadata={"description": "Annual interest rate, as a percentage."},
        **kwargs,
    )


def term_months_field(**kwargs) -> fields.Integer:
    return fields.Integer(
        error_messages={**REQUIRED_MESSAGES, "invalid": "Debe ser un número entero."},
        validate=validate.Range(min=1, max=360, error="El plazo debe estar entre {min} y {max} meses."),
        **kwargs,
    )


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
    amount = amount_field(required=True)
    interest_rate = interest_rate_field(required=True)
    term_months = term_months_field(required=True, strict=True)
    issue_date = fields.Date(
        required=True,
        error_messages=DATE_MESSAGES,
        validate=[
            validate.Range(min=MIN_ISSUE_DATE, error="La fecha debe ser posterior al 01/01/2000."),
            not_in_future,
        ],
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @pre_load
    def normalize_client_name(self, data, **kwargs):
        # Trim and collapse repeated spaces so "  Ana   Paz " is stored as "Ana Paz"
        if isinstance(data, dict) and isinstance(data.get("client_name"), str):
            data = {**data, "client_name": " ".join(data["client_name"].split())}
        return data


class DateRangeSchema(Schema):
    issue_date_from = fields.Date(error_messages=DATE_MESSAGES, metadata={"description": "Issued on or after this date."})
    issue_date_to = fields.Date(error_messages=DATE_MESSAGES, metadata={"description": "Issued on or before this date."})

    @validates_schema
    def validate_date_range(self, data, **kwargs):
        start, end = data.get("issue_date_from"), data.get("issue_date_to")
        if start and end and start > end:
            raise ValidationError("La fecha final debe ser igual o posterior a la inicial.", field_name="issue_date_to")


class CreditFilterSchema(DateRangeSchema):
    client_name = fields.String(metadata={"description": "Case-insensitive 'contains' filter on the client name."})
    amount_min = fields.Decimal(places=2, error_messages=NUMBER_MESSAGES, validate=validate.Range(min=0))
    amount_max = fields.Decimal(places=2, error_messages=NUMBER_MESSAGES, validate=validate.Range(min=0))

    @validates_schema
    def validate_amount_range(self, data, **kwargs):
        low, high = data.get("amount_min"), data.get("amount_max")
        if low is not None and high is not None and low > high:
            raise ValidationError("El monto máximo debe ser igual o mayor al mínimo.", field_name="amount_max")


class CreditExportQuerySchema(CreditFilterSchema):
    sort = fields.String(load_default="id", validate=validate.OneOf(SORT_FIELDS))
    order = fields.String(load_default="asc", validate=validate.OneOf(("asc", "desc")))


class CreditQuerySchema(CreditExportQuerySchema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=10, validate=validate.Range(min=1, max=100))


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


class TopClientSchema(Schema):
    client_name = fields.String()
    credits = fields.Integer()
    total_amount = fields.Decimal(places=2, as_string=True)


class CreditSummarySchema(Schema):
    total_credits = fields.Integer()
    total_amount = fields.Decimal(places=2, as_string=True)
    average_amount = fields.Decimal(places=2, as_string=True)
    average_interest_rate = fields.Decimal(places=2, as_string=True)
    average_term_months = fields.Decimal(places=1, as_string=True)
    monthly = fields.List(fields.Nested(MonthlyTotalSchema))
    by_term = fields.List(fields.Nested(TermRangeSchema))
    top_clients = fields.List(fields.Nested(TopClientSchema))


class QuoteQuerySchema(Schema):
    amount = amount_field(required=True)
    interest_rate = interest_rate_field(required=True)
    term_months = term_months_field(required=True)


class QuoteSchema(Schema):
    monthly_payment = fields.Decimal(places=2, as_string=True)
    total_interest = fields.Decimal(places=2, as_string=True)
    total_paid = fields.Decimal(places=2, as_string=True)


class InstallmentSchema(Schema):
    number = fields.Integer()
    due_date = fields.Date()
    payment = fields.Decimal(places=2, as_string=True)
    interest = fields.Decimal(places=2, as_string=True)
    principal = fields.Decimal(places=2, as_string=True)
    balance = fields.Decimal(places=2, as_string=True)


class AmortizationSchema(QuoteSchema):
    installments = fields.List(fields.Nested(InstallmentSchema))


class CreditChangeSchema(Schema):
    id = fields.Integer()
    action = fields.String(metadata={"description": "created or updated."})
    changes = fields.Dict(metadata={"description": "{field: {old, new}} with values as strings."})
    changed_at = fields.DateTime()
    changed_by = fields.Function(
        lambda change: change.user.full_name if change.user else None,
        metadata={"description": "Name of the user who made the change, or null when unknown."},
    )
