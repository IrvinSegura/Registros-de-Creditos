"""REST endpoints for credits. Translates HTTP to service calls and nothing else."""

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import CreditPageSchema, CreditQuerySchema, CreditSchema, CreditSummarySchema
from app.services import credit_service

blp = Blueprint("credits", __name__, url_prefix="/api/v1/credits", description="Credit registration and lookup.")


@blp.route("")
class CreditsResource(MethodView):
    @blp.arguments(CreditQuerySchema, location="query")
    @blp.response(200, CreditPageSchema)
    def get(self, filters):
        """List credits, paginated and optionally filtered by client name."""
        page = credit_service.list_credits(**filters)
        return {
            "items": page.items,
            "meta": {"page": page.page, "per_page": page.per_page, "total": page.total, "pages": page.pages},
        }

    @blp.arguments(CreditSchema)
    @blp.response(201, CreditSchema)
    def post(self, data):
        """Register a new credit."""
        return credit_service.create_credit(data)


@blp.route("/summary")
class CreditSummaryResource(MethodView):
    @blp.response(200, CreditSummarySchema)
    def get(self):
        """Portfolio totals and breakdowns for the dashboard."""
        return credit_service.get_summary()


@blp.route("/<int:credit_id>")
class CreditResource(MethodView):
    @blp.response(200, CreditSchema)
    @blp.alt_response(404, response="NOT_FOUND")
    def get(self, credit_id):
        """Get a credit by id."""
        return credit_service.get_credit(credit_id)

    @blp.arguments(CreditSchema)
    @blp.response(200, CreditSchema)
    @blp.alt_response(404, response="NOT_FOUND")
    def put(self, data, credit_id):
        """Replace a credit's data."""
        return credit_service.update_credit(credit_id, data)

    @blp.response(204)
    @blp.alt_response(404, response="NOT_FOUND")
    def delete(self, credit_id):
        """Delete a credit."""
        credit_service.delete_credit(credit_id)
