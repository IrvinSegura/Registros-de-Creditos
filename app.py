# Description: Main file to run the application.
from flask import Flask
from flask_cors import CORS
from config import Config
from models import db
from routes import creditos_bp

# Creating the Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initializing the database
db.init_app(app)
CORS(app)

# Registering the blueprint
app.register_blueprint(creditos_bp, url_prefix="/creditos")

# Running the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
