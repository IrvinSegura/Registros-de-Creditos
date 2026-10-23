"""REST endpoints for credits and their payments. Translates HTTP to service calls and nothing else."""

from flask import Response, request
from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint

from app import clock
from app.auth.permissions import (
    ARCHIVE_CREDITS,
    CREATE_CREDITS,
    DELETE_CREDITS,
    DELETE_PAYMENTS,
    RECORD_PAYMENTS,
    UPDATE_CREDITS,
    require_permission,
)
from app.schemas import (
    AmortizationSchema,
    CreditChangeSchema,
    CreditExportQuerySchema,
    CreditPageSchema,
    CreditQuerySchema,
    CreditSchema,
    CreditSummarySchema,
    DateRangeSchema,
    PaymentSchema,
    QuoteQuerySchema,
    QuoteSchema,
    StatementQuerySchema,
)
from app.services import credit_service, report_service
from app.services.credit_service import StaleCreditError

blp = Blueprint(
    "credits",
    __name__,
    url_prefix="/api/v1/credits",
    description=(
        "Credit registration, payments and lookup. Every endpoint requires a signed-in session; "
        "state-changing requests also need the X-CSRF-Token header."
    ),
)

MIME_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _download(body: str | bytes, filename: str, file_format: str) -> Response:
    return Response(
        body,
        mimetype=MIME_TYPES[file_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _expected_version() -> int | None:
    """The credit version sent in If-Match ("3" or W/"3"); None when the client sends none or "*"."""
    header = request.headers.get("If-Match", "").strip()
    if not header or header == "*":
        return None
    value = header.removeprefix("W/").strip('"')
    if not value.isdigit():
        raise StaleCreditError()
    return int(value)


@blp.route("")
class CreditsResource(MethodView):
    @blp.arguments(CreditQuerySchema, location="query")
    @blp.response(200, CreditPageSchema)
    def get(self, filters):
        """List credits, paginated, sorted and optionally filtered. Archived credits only with status=archived."""
        page, per_page = filters.pop("page"), filters.pop("per_page")
        items, total = credit_service.list_credits(page, per_page, **filters)
        return {
            "items": items,
            "meta": {"page": page, "per_page": per_page, "total": total, "pages": -(-total // per_page)},
        }

    # Permission checks go first, so a read-only user gets 403 before the body is validated
    @require_permission(CREATE_CREDITS)
    @blp.arguments(CreditSchema)
    @blp.response(201, CreditSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    def post(self, data):
        """Register a new credit. Requires the analyst or admin role."""
        return credit_service.create_credit(data, user_id=current_user.id)


@blp.route("/export")
class CreditExportResource(MethodView):
    @blp.arguments(CreditExportQuerySchema, location="query")
    @blp.response(200, content_type="text/csv", description="The filtered credits as a CSV, Excel (xlsx) or PDF file.")
    def get(self, query):
        """Download the filtered credits as a CSV, Excel or PDF file."""
        file_format = query.pop("format")
        if file_format == "csv":
            body = credit_service.export_csv(**query)
        else:
            body = report_service.portfolio_report(credit_service.credits_for_export(**query), file_format, query)
        return _download(body, f"creditos-{clock.today().isoformat()}.{file_format}", file_format)


@blp.route("/summary")
class CreditSummaryResource(MethodView):
    @blp.arguments(DateRangeSchema, location="query")
    @blp.response(200, CreditSummarySchema)
    def get(self, period):
        """Portfolio totals and breakdowns for the dashboard, optionally for an issue-date period."""
        return credit_service.get_summary(**period)


@blp.route("/quote")
class CreditQuoteResource(MethodView):
    @blp.arguments(QuoteQuerySchema, location="query")
    @blp.response(200, QuoteSchema)
    def get(self, terms):
        """Estimate the monthly payment of a credit before registering it."""
        return credit_service.get_quote(**terms)


@blp.route("/<int:credit_id>")
class CreditResource(MethodView):
    @blp.response(200, CreditSchema)
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Get a credit by id. The ETag header carries its version."""
        credit = credit_service.get_credit(credit_id)
        return credit, 200, {"ETag": f'"{credit.version}"'}

    @require_permission(UPDATE_CREDITS)
    @blp.arguments(CreditSchema)
    @blp.response(200, CreditSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    @blp.alt_response(409, response="DEFAULT_ERROR", description="The credit is archived.")
    @blp.alt_response(412, response="DEFAULT_ERROR", description="If-Match does not match the current version.")
    def put(self, data, credit_id):
        """Replace a credit's data. Requires the analyst or admin role.

        Send the version you edited in If-Match ("3"): if someone saved the credit since, the answer is 412.
        """
        credit = credit_service.update_credit(
            credit_id, data, user_id=current_user.id, expected_version=_expected_version()
        )
        return credit, 200, {"ETag": f'"{credit.version}"'}

    @require_permission(DELETE_CREDITS)
    @blp.response(204)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    @blp.alt_response(409, response="DEFAULT_ERROR", description="The credit is not archived.")
    def delete(self, credit_id):
        """Delete an archived credit for good, with its payments and history. Requires the admin role."""
        credit_service.delete_credit(credit_id, user_id=current_user.id)


@blp.route("/<int:credit_id>/archive")
class CreditArchiveResource(MethodView):
    @require_permission(ARCHIVE_CREDITS)
    @blp.response(200, CreditSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def post(self, credit_id):
        """Take a credit out of the portfolio, keeping its data. Requires the admin role."""
        return credit_service.archive_credit(credit_id, user_id=current_user.id)


@blp.route("/<int:credit_id>/restore")
class CreditRestoreResource(MethodView):
    @require_permission(ARCHIVE_CREDITS)
    @blp.response(200, CreditSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def post(self, credit_id):
        """Bring an archived credit back to the portfolio. Requires the admin role."""
        return credit_service.restore_credit(credit_id, user_id=current_user.id)


@blp.route("/<int:credit_id>/amortization")
class CreditAmortizationResource(MethodView):
    @blp.response(200, AmortizationSchema)
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Monthly payment schedule of a credit (fixed installments), with each installment's status."""
        return credit_service.get_amortization(credit_id)


@blp.route("/<int:credit_id>/statement")
class CreditStatementResource(MethodView):
    @blp.arguments(StatementQuerySchema, location="query")
    @blp.response(200, content_type="application/pdf", description="Account statement as a PDF or Excel (xlsx) file.")
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, query, credit_id):
        """Download a credit's account statement: data, standing, schedule and payments."""
        file_format = query["format"]
        body = report_service.statement(credit_service.get_credit(credit_id), file_format)
        return _download(body, f"estado-de-cuenta-{credit_id}-{clock.today().isoformat()}.{file_format}", file_format)


@blp.route("/<int:credit_id>/history")
class CreditHistoryResource(MethodView):
    @blp.response(200, CreditChangeSchema(many=True))
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Changes made to a credit, newest first."""
        return credit_service.get_history(credit_id)


@blp.route("/<int:credit_id>/payments")
class CreditPaymentsResource(MethodView):
    @blp.response(200, PaymentSchema(many=True))
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Payments recorded for a credit, newest first."""
        return credit_service.list_payments(credit_id)

    @require_permission(RECORD_PAYMENTS)
    @blp.arguments(PaymentSchema)
    @blp.response(201, PaymentSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    @blp.alt_response(409, response="DEFAULT_ERROR", description="The credit is archived or already paid off.")
    def post(self, data, credit_id):
        """Record a payment. It cannot exceed what is left to pay. Requires the analyst or admin role."""
        return credit_service.record_payment(credit_id, data, user_id=current_user.id)


@blp.route("/<int:credit_id>/payments/<int:payment_id>")
class CreditPaymentResource(MethodView):
    @require_permission(DELETE_PAYMENTS)
    @blp.response(204)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def delete(self, credit_id, payment_id):
        """Remove a payment recorded by mistake; the history keeps a trace. Requires the admin role."""
        credit_service.delete_payment(credit_id, payment_id, user_id=current_user.id)
