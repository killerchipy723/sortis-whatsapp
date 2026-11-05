from flask import Flask
from config import Config
from routes.auth_routes import auth_bp
from routes.cliente_routes import cliente_bp
from routes.mensaje_routes import mensaje_bp
from scheduler.scheduler import iniciar_scheduler
from routes.webhook_routes import webhook_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registro de Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(mensaje_bp)
    app.register_blueprint(webhook_bp)
    
    from flask import Response

    @app.route('/privacidad', methods=['GET'])
    def privacidad():
        html_content = """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Politica de Privacidad - Sortis Motos</title>
        </head>
        <body>
            <h1>Politica de Privacidad</h1>
            <p>Los datos recabados a través de esta plataforma de atención automatizada se utilizan exclusivamente para la gestión y consulta de cuotas de los clientes de Sortis Motos.</p>
        </body>
        </html>
        """
        return Response(html_content, status=200, mimetype='text/html')

    # Inicializar el scheduler de forma segura al crear la app
    # (Usamos un flag o validación simple si corre con reloader para evitar doble ejecución)
    try:
        iniciar_scheduler()
    except Exception as e:
        print(f"⚠️ [Scheduler] No se pudo iniciar: {e}")

    return app

if __name__ == '__main__':
    app = create_app()
    # Recomendado: desactivar el modo debug (debug=False) para producción en el VPS
    app.run(host='0.0.0.0', port=7410, debug=False)