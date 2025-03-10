from flask import Flask, request, jsonify
from models import db, Credito
from config import SQLALCHEMY_DATABASE_URI
from flask_cors import CORS
from flask import render_template
from marshmallow import Schema, fields, ValidationError
import re

# Creating the Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db.init_app(app)

# Defining the schema for the credit
class CreditoSchema(Schema):
    cliente = fields.String(required=True)
    monto = fields.Float(required=True)
    tasa_interes = fields.Float(required=True)
    plazo = fields.Integer(required=True)
    fecha_otorgamiento = fields.Date(required=True)

    def validate_cliente(self, value):
        if len(value) < 5:
            raise ValidationError('El nombre del cliente debe tener al menos 5 caracteres')
    
    def validate_monto(self, value):
        if value <= 0:
            raise ValidationError('El monto del crédito debe ser mayor a 0')
    
    def validate_tasa_interes(self, value):
        if value <= 0:
            raise ValidationError('La tasa de interés debe ser mayor a 0')
    
    def validate_plazo(self, value):
        if value <= 0:
            raise ValidationError('El plazo del crédito debe ser mayor a 0')
    
    def validate_fecha_otorgamiento(self, value):
        if value.year < 2000:
            raise ValidationError('La fecha de otorgamiento debe ser mayor al año 2000')

# Creating the database
with app.app_context():
    db.create_all()

# Defining the routes
@app.route('/')
def index():
    return render_template('index.html')

# Route to add a new credit
@app.route('/creditos', methods=['POST'])
def agregar_credito():
    data = request.json
    try:
        credito_schema = CreditoSchema()
        credito_schema.load(data)
        
        nuevo_credito = Credito(
            cliente=data['cliente'],
            monto=data['monto'],
            tasa_interes=data['tasa_interes'],
            plazo=data['plazo'],
            fecha_otorgamiento=data['fecha_otorgamiento']
        )
        db.session.add(nuevo_credito)
        db.session.commit()
        return jsonify({'message': 'Crédito registrado correctamente'}), 201
    except ValidationError as err:
        return jsonify(err.messages), 400

# Route to list all credits
@app.route('/creditos', methods=['GET'])
def listar_creditos():
    creditos = Credito.query.all()
    return jsonify([{
        'id': c.id, 'cliente': c.cliente, 'monto': c.monto, 'tasa_interes': c.tasa_interes,
        'plazo': c.plazo, 'fecha_otorgamiento': c.fecha_otorgamiento
    } for c in creditos])

# Route to get, edit and delete a credit
@app.route('/creditos/<int:id>', methods=['GET', 'PUT'])
def editar_credito(id):
    if request.method == 'GET':
        credito = Credito.query.get(id)
        if not credito:
            return jsonify({'error': 'Crédito no encontrado'}), 404
        return jsonify({
            'id': credito.id, 'cliente': credito.cliente, 'monto': credito.monto,
            'tasa_interes': credito.tasa_interes, 'plazo': credito.plazo,
            'fecha_otorgamiento': credito.fecha_otorgamiento
        })
    
    if request.method == 'PUT':
        data = request.json
        try:
            credito_schema = CreditoSchema()
            credito_schema.load(data)

            credito = Credito.query.get(id)
            if not credito:
                return jsonify({'error': 'Crédito no encontrado'}), 404
            
            credito.cliente = data['cliente']
            credito.monto = data['monto']
            credito.tasa_interes = data['tasa_interes']
            credito.plazo = data['plazo']
            credito.fecha_otorgamiento = data['fecha_otorgamiento']
            db.session.commit()
            return jsonify({'message': 'Crédito actualizado correctamente'})
        except ValidationError as err:
            return jsonify(err.messages), 400

# Route to delete a credit
@app.route('/creditos/<int:id>', methods=['DELETE'])
def eliminar_credito(id):
    credito = Credito.query.get(id)
    if not credito:
        return jsonify({'error': 'Crédito no encontrado'}), 404
    db.session.delete(credito)
    db.session.commit()
    return jsonify({'message': 'Crédito eliminado correctamente'})

if __name__ == '__main__':
    app.run(debug=True)
