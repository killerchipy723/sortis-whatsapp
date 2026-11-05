from flask import Blueprint, request, jsonify
from services.bot_service import BotService

webhook_bp = Blueprint('webhook_bp', __name__)

# Token de verificación que configuras en el panel de Meta Developers (Webhook -> Verify Token)
VERIFY_TOKEN = "sortis_motos_token_secreto"

@webhook_bp.route('/webhook', methods=['GET'])
def verificar_webhook():
    """
    Validación inicial obligatoria que exige Meta al configurar la URL del Webhook.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("✅ [Webhook] Verificado correctamente por Meta.")
            return challenge, 200
        else:
            print("❌ [Webhook] Error: El token de verificación no coincide.")
            return "Error de verificación", 403
    return "Parámetros inválidos", 400


@webhook_bp.route('/webhook', methods=['POST'])
def recibir_mensajes():
    """
    Recepción en tiempo real de mensajes, respuestas de botones y eventos de WhatsApp.
    """
    body = request.get_json()

    try:
        if body.get('object') == 'whatsapp_business_account':
            for entry in body.get('entry', []):
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    messages = value.get('messages')
                    
                    if messages:
                        msg = messages[0]
                        from_phone = msg.get('from') # Número de teléfono del cliente (ej. 549387...)
                        msg_type = msg.get('type')
                        
                        # 1. Si el usuario envió un mensaje de texto normal (ej. DNI)
                        if msg_type == 'text':
                            texto_usuario = msg['text']['body'].strip()
                            print(f"📩 [Mensaje recibido] De: {from_phone} - Texto: {texto_usuario}")
                            BotService.manejar_mensaje_entrante(from_phone, texto_usuario=texto_usuario)
                            
                        # 2. Si el usuario hizo clic en un botón interactivo del menú
                        elif msg_type == 'interactive':
                            button_reply = msg.get('interactive', {}).get('button_reply', {})
                            button_id = button_reply.get('id')
                            print(f"🔘 [Botón presionado] De: {from_phone} - ID: {button_id}")
                            BotService.manejar_mensaje_entrante(from_phone, texto_usuario="", button_id=button_id)

            return jsonify({"status": "EVENT_RECEIVED"}), 200
            
    except Exception as e:
        print(f"❌ [Error en Webhook]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "ignored"}), 200