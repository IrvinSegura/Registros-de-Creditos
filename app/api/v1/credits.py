"""REST endpoints for credits. Translates HTTP to service calls and nothing else."""

from datetime import date

from flask import Response
from flask.views import MethodView
from flask_login import current_user
from flask_smorest import Blueprint

from app.auth.permissions import CREATE_CREDITS, DELETE_CREDITS, UPDATE_CREDITS, require_permission
from app.schemas import (
    AmortizationSchema,
    CreditChangeSchema,
    CreditExportQuerySchema,
    CreditPageSchema,
    CreditQuerySchema,
    CreditSchema,
    CreditSummarySchema,
    DateRangeSchema,
    QuoteQuerySchema,
    QuoteSchema,
)
from app.services import credit_service

blp = Blueprint(
    "credits",
    __name__,
    url_prefix="/api/v1/credits",
    description=(
        "Credit registration and lookup. Every endpoint requires a signed-in session; "
        "state-changing requests also need the X-CSRF-Token header."
    ),
)


@blp.route("")
class CreditsResource(MethodView):
    @blp.arguments(CreditQuerySchema, location="query")
    @blp.response(200, CreditPageSchema)
    def get(self, filters):
        """List credits, paginated, sorted and optionally filtered."""
        page = credit_service.list_credits(**filters)
        return {
            "items": page.items,
            "meta": {"page": page.page, "per_page": page.per_page, "total": page.total, "pages": page.pages},
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
    @blp.response(200, content_type="text/csv", description="CSV file with the filtered credits.")
    def get(self, filters):
        """Download the filtered credits as a CSV file."""
        filename = f"creditos-{date.today().isoformat()}.csv"
        return Response(
            credit_service.export_csv(**filters),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


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
        """Get a credit by id."""
        return credit_service.get_credit(credit_id)

    @require_permission(UPDATE_CREDITS)
    @blp.arguments(CreditSchema)
    @blp.response(200, CreditSchema)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def put(self, data, credit_id):
        """Replace a credit's data. Requires the analyst or admin role."""
        return credit_service.update_credit(credit_id, data, user_id=current_user.id)

    @require_permission(DELETE_CREDITS)
    @blp.response(204)
    @blp.alt_response(403, response="FORBIDDEN")
    @blp.alt_response(404, response="NOT_FOUND")
    def delete(self, credit_id):
        """Delete a credit and its history. Requires the admin role."""
        credit_service.delete_credit(credit_id)


@blp.route("/<int:credit_id>/amortization")
class CreditAmortizationResource(MethodView):
    @blp.response(200, AmortizationSchema)
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Monthly payment schedule of a credit (fixed installments)."""
        return credit_service.get_amortization(credit_id)


@blp.route("/<int:credit_id>/history")
class CreditHistoryResource(MethodView):
    @blp.response(200, CreditChangeSchema(many=True))
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Changes made to a credit, newest first."""
        return credit_service.get_history(credit_id)
