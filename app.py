# Description: Main file to run the application.
from flask import Flask
from flask_cors import CORS

from config import Config
from models import db
from routes import credits_bp


def create_app(config_class=Config):
    # Creating the Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initializing the database
    db.init_app(app)
    CORS(app)

    # Registering the blueprint
    app.register_blueprint(credits_bp)

    with app.app_context():
        db.create_all()

    return app


# Running the app
if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config["DEBUG"])
