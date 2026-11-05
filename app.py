import logging
from flask import Flask, request, jsonify
from services.whatsapp_service import WhatsAppService

# Configuración básica de logs
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Token de verificación que configuraste en el panel de Meta para el Webhook
VERIFY_TOKEN = "sortis_motos_token_seguro"

@app.route("/", methods=["GET"])
def home():
    return "Servidor de Sortis Motos Activo y Funcionando", 200


@app.route("/privacidad", methods=["GET"])
def privacidad():
    """Endpoint requerido por Meta para validar la política de privacidad."""
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
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Verificación del Webhook requerida por Meta."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logging.info("Webhook verificado correctamente por Meta.")
            return challenge, 200
        else:
            return "Token de verificación inválido", 403
    return "Parámetros faltantes", 400


@app.route("/webhook", methods=["POST"])
def recibir_webhook():
    """Recepción y procesamiento de mensajes entrantes desde WhatsApp."""
    try:
        data = request.get_json()
        logging.info("Datos recibidos del webhook: %s", data)

        # Validar estructura de la petición de WhatsApp
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Verificar si hay mensajes entrantes
                    if "messages" in value:
                        messages = value["messages"]
                        for message in messages:
                            remitente = message.get("from")
                            
                            # 1. Caso: El usuario escribió un mensaje de texto plano (ej. "Hola")
                            if "text" in message:
                                texto_ingresado = message["text"]["body"].strip().lower()
                                logging.info(f"Mensaje de texto recibido de {remitente}: {texto_ingresado}")
                                
                                # Enviar el menú principal con botones interactivos
                                WhatsAppService.enviar_menu_principal(remitente)

                            # 2. Caso: El usuario presionó un botón interactivo
                            elif "interactive" in message:
                                interactive = message["interactive"]
                                if interactive.get("type") == "button_reply":
                                    button_id = interactive["button_reply"]["id"]
                                    logging.info(f"Botón presionado por {remitente}: {button_id}")

                                    if button_id == "btn_cliente":
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "Por favor, ingresa tu número de DNI para consultar tus cuotas:"
                                        )
                                    elif button_id == "btn_no_cliente":
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "¡Perfecto! Un asesor se pondrá en contacto contigo a la brevedad."
                                        )

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"Error procesando el webhook de WhatsApp: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7410, debug=False)