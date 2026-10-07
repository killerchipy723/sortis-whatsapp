from flask import Flask
from config import Config
from routes.auth_routes import auth_bp
from routes.cliente_routes import cliente_bp
from routes.mensaje_routes import mensaje_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registro de Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(mensaje_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=4000, debug=True)