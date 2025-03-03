from flask import Flask, request, jsonify
from models import db, Credito
from config import SQLALCHEMY_DATABASE_URI
from flask_cors import CORS
from flask import render_template

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db.init_app(app)

# Crear la base de datos
with app.app_context():
    db.create_all()

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para agregar crédito
@app.route('/creditos', methods=['POST'])
def agregar_credito():
    data = request.json
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

# Ruta para obtener todos los créditos
@app.route('/creditos', methods=['GET'])
def listar_creditos():
    creditos = Credito.query.all()
    return jsonify([{
        'id': c.id, 'cliente': c.cliente, 'monto': c.monto, 'tasa_interes': c.tasa_interes,
        'plazo': c.plazo, 'fecha_otorgamiento': c.fecha_otorgamiento
    } for c in creditos])

# Ruta para obtener y editar crédito
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

# Ruta para eliminar crédito
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
