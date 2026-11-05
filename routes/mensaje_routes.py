from flask import Blueprint, request, jsonify, send_file
from models.mensaje import CuotaModel
from services.mensaje_service import ReciboService
from services.whatsapp_service import WhatsAppService
from config import Config

mensaje_bp = Blueprint('mensaje', __name__)

# ==========================================
# RUTAS DE GESTIÓN DE CUOTAS Y PDF (Existentes)
# ==========================================

@mensaje_bp.route('/update-cuota', methods=['POST'])
def update_cuota():
    data = request.json or request.form
    
    try:
        idcuota = int(data.get('idcuota'))
        importe = float(data.get('importe'))
        nrecibo = int(data.get('nrecibo'))
        idvendedor = int(data.get('idvendedor'))
        fechapago = data.get('fechapago')
        formapago = data.get('formapago')
        obs = data.get('obs')
        estado = data.get('estado')
    except (TypeError, ValueError):
        return "Datos no válidos", 400

    exito = CuotaModel.actualizar_cuota(idcuota, importe, formapago, nrecibo, fechapago, idvendedor, obs, estado)
    if exito:
        return "Cuota actualizada correctamente", 200
    return "Cuota no encontrada", 404

@mensaje_bp.route('/generar-pdf/<int:idc>', methods=['GET'])
def generar_pdf(idc):
    buffer = ReciboService.generar_pdf_recibo(idc)
    if not buffer:
        return "No se encontró la cuota", 404

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"OrdenPago-{idc}.pdf",
        mimetype='application/pdf'
    )


# ==========================================
# RUTAS DE WHATSAPP WEBHOOK (Nuevas)
# ==========================================

@mensaje_bp.route('/webhook', methods=['GET'])
def verificar_webhook():
    """Validación inicial del Webhook requerida por Meta."""
    token_ingresado = request.args.get("hub.verify_token")
    reto = request.args.get("hub.challenge")
    
    if token_ingresado == Config.VERIFY_TOKEN:
        return str(reto), 200
    return "Token de verificación inválido", 403


@mensaje_bp.route('/webhook', methods=['POST'])
def recibir_webhook():
    """Recepción de mensajes y botones interactivos enviados por los clientes."""
    data = request.get_json()
    
    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    if messages:
                        msg = messages[0]
                        remitente = msg.get("from") # Número de teléfono del cliente
                        
                        # Manejo de respuestas a botones interactivos
                        if msg.get("type") == "interactive":
                            btn_id = msg.get("interactive", {}).get("button_reply", {}).get("id")
                            if btn_id == "btn_cuotas":
                                WhatsAppService.enviar_mensaje_texto(remitente, "Para consultar el estado de tus cuotas, por favor indicanos tu DNI.")
                            elif btn_id == "btn_planes":
                                WhatsAppService.enviar_mensaje_texto(remitente, "Podés comunicarte con un asesor de Sortis Motos para conocer las motos y planes disponibles.")
                            elif btn_id == "btn_asesor":
                                WhatsAppService.enviar_mensaje_texto(remitente, "Un asesor se pondrá en contacto contigo a la brevedad.")
                        
                        # Manejo de mensajes de texto comunes
                        elif msg.get("type") == "text":
                            texto_usuario = msg.get("text", {}).get("body", "").strip().lower()
                            if "hola" in texto_usuario:
                                WhatsAppService.enviar_menu_principal(remitente)
                            else:
                                WhatsAppService.enviar_mensaje_texto(remitente, "¡Gracias por comunicarte con Sortis Motos! Escribí 'Hola' para ver las opciones disponibles.")
                                
            return jsonify({"status": "received"}), 200
            
    except Exception as e:
        print(f"Error procesando el webhook de WhatsApp: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "ignored"}), 200