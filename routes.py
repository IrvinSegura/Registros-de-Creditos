from flask import Blueprint, jsonify, render_template, request
from marshmallow import Schema, ValidationError, fields, validates

from models import Credit, db

credits_bp = Blueprint("credits", __name__)


# Defining the schema for the credit
class CreditSchema(Schema):
    cliente = fields.String(required=True)
    monto = fields.Float(required=True)
    tasa_interes = fields.Float(required=True)
    plazo = fields.Integer(required=True)
    fecha_otorgamiento = fields.Date(required=True)

    @validates("cliente")
    def validate_client(self, value, **kwargs):
        if len(value) < 5:
            raise ValidationError('El nombre del cliente debe tener al menos 5 caracteres')

    @validates("monto")
    def validate_amount(self, value, **kwargs):
        if value <= 0:
            raise ValidationError('El monto del crédito debe ser mayor a 0')

    @validates("tasa_interes")
    def validate_interest_rate(self, value, **kwargs):
        if value <= 0:
            raise ValidationError('La tasa de interés debe ser mayor a 0')

    @validates("plazo")
    def validate_term(self, value, **kwargs):
        if value <= 0:
            raise ValidationError('El plazo del crédito debe ser mayor a 0')

    @validates("fecha_otorgamiento")
    def validate_issue_date(self, value, **kwargs):
        if value.year < 2000:
            raise ValidationError('La fecha de otorgamiento debe ser mayor al año 2000')


credit_schema = CreditSchema()


def serialize_credit(credit):
    return {
        'id': credit.id, 'cliente': credit.cliente, 'monto': credit.monto,
        'tasa_interes': credit.tasa_interes, 'plazo': credit.plazo,
        'fecha_otorgamiento': credit.fecha_otorgamiento
    }


def load_payload():
    # Only validated data reaches the model; the date is stored as ISO text
    data = credit_schema.load(request.get_json(silent=True) or {})
    data['fecha_otorgamiento'] = data['fecha_otorgamiento'].isoformat()
    return data


# Defining the routes
@credits_bp.route('/')
def index():
    return render_template('index.html')


# Route to add a new credit
@credits_bp.route('/creditos', methods=['POST'])
def create_credit():
    try:
        data = load_payload()
    except ValidationError as err:
        return jsonify(err.messages), 400

    db.session.add(Credit(**data))
    db.session.commit()
    return jsonify({'message': 'Crédito registrado correctamente'}), 201


# Route to list all credits
@credits_bp.route('/creditos', methods=['GET'])
def list_credits():
    credits = db.session.scalars(db.select(Credit).order_by(Credit.id)).all()
    return jsonify([serialize_credit(c) for c in credits])


# Route to get a credit
@credits_bp.route('/creditos/<int:credit_id>', methods=['GET'])
def get_credit(credit_id):
    credit = db.session.get(Credit, credit_id)
    if not credit:
        return jsonify({'error': 'Crédito no encontrado'}), 404
    return jsonify(serialize_credit(credit))


# Route to edit a credit
@credits_bp.route('/creditos/<int:credit_id>', methods=['PUT'])
def update_credit(credit_id):
    credit = db.session.get(Credit, credit_id)
    if not credit:
        return jsonify({'error': 'Crédito no encontrado'}), 404
    try:
        data = load_payload()
    except ValidationError as err:
        return jsonify(err.messages), 400

    for field, value in data.items():
        setattr(credit, field, value)
    db.session.commit()
    return jsonify({'message': 'Crédito actualizado correctamente'})


# Route to delete a credit
@credits_bp.route('/creditos/<int:credit_id>', methods=['DELETE'])
def delete_credit(credit_id):
    credit = db.session.get(Credit, credit_id)
    if not credit:
        return jsonify({'error': 'Crédito no encontrado'}), 404
    db.session.delete(credit)
    db.session.commit()
    return jsonify({'message': 'Crédito eliminado correctamente'})
