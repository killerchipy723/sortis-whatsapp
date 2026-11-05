import logging
import mysql.connector
from flask import Flask, request, jsonify
from services.whatsapp_service import WhatsAppService
from config import Config  # Asegúrate de tener aquí los datos de conexión a MySQL

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

VERIFY_TOKEN = "sortis_motos_token_seguro"

def obtener_conexion_db():
    """Establece conexión con la base de datos MySQL."""
    return mysql.connector.connect(
        host=getattr(Config, 'DB_HOST', 'localhost'),
        user=getattr(Config, 'DB_USER', 'tu_usuario'),
        password=getattr(Config, 'DB_PASSWORD', 'tu_contraseña'),
        database=getattr(Config, 'DB_NAME', 'sortis_motos')
    )

@app.route("/", methods=["GET"])
def home():
    return "Servidor de Sortis Motos Activo y Funcionando", 200


@app.route("/privacidad", methods=["GET"])
def privacidad():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"><title>Política de Privacidad - Sortis Motos</title></head>
    <body>
        <h1>Política de Privacidad</h1>
        <p>Los datos recopilados se utilizan exclusivamente para la gestión y consulta de cuotas de clientes.</p>
    </body>
    </html>
    """
    return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
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
    try:
        data = request.get_json()
        logging.info("Datos recibidos del webhook: %s", data)

        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    if "messages" in value:
                        messages = value["messages"]
                        for message in messages:
                            remitente = message.get("from")
                            
                            # 1. Mensajes de texto (Saludos o DNI ingresado)
                            if "text" in message:
                                texto_ingresado = message["text"]["body"].strip()
                                logging.info(f"Texto recibido de {remitente}: {texto_ingresado}")
                                
                                # Si el usuario ingresó un DNI (7 u 8 dígitos)
                                if texto_ingresado.isdigit() and 7 <= len(texto_ingresado) <= 8:
                                    dni = texto_ingresado
                                    try:
                                        conn = obtener_conexion_db()
                                        cursor = conn.cursor(dictionary=True)
                                        
                                        # Buscar afiliado y sus planes asociados por DNI
                                        # (Ajusta la tabla 'afiliados' o 'clientes' según corresponda en tu BD)
                                        query_afiliado = """
                                            SELECT DISTINCT apf.idplan, apf.idalta 
                                            FROM altaplanafil apf
                                            INNER JOIN afiliados a ON apf.idafiliado = a.idafiliado
                                            WHERE a.dni = %s
                                        """
                                        cursor.execute(query_afiliado, (dni,))
                                        planes = cursor.fetchall()
                                        
                                        cursor.close()
                                        conn.close()

                                        if planes:
                                            # Creamos botones con los planes encontrados (máximo 3 soportados por WhatsApp)
                                            botones_planes = []
                                            for p in planes[:3]:
                                                id_plan_str = str(p['idplan'])
                                                botones_planes.append({
                                                    "id": f"plan_{id_plan_str}",
                                                    "title": f"Plan {id_plan_str}"[:20]
                                                })
                                            
                                            WhatsAppService.enviar_menu_botones(
                                                remitente, 
                                                f"Hemos encontrado planes asociados al DNI {dni}. Selecciona el plan a consultar:", 
                                                botones_planes
                                            )
                                        else:
                                            WhatsAppService.enviar_mensaje_texto(
                                                remitente, 
                                                f"No encontramos registros activos con el DNI {dni}. Por favor, verifica el número e inténtalo de nuevo."
                                            )
                                    except Exception as db_err:
                                        logging.error(f"Error de base de datos: {str(db_err)}")
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "Ocurrió un error al consultar tus datos. Inténtalo más tarde."
                                        )
                                else:
                                    # Saludo o texto genérico -> Muestra menú principal
                                    WhatsAppService.enviar_menu_principal(remitente)

                            # 2. Respuestas a Botones Interactivos
                            elif "interactive" in message:
                                interactive = message["interactive"]
                                if interactive.get("type") == "button_reply":
                                    button_id = interactive["button_reply"]["id"]
                                    logging.info(f"Botón presionado por {remitente}: {button_id}")

                                    if button_id == "btn_cliente":
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "Por favor, ingresa tu número de DNI para buscar tus planes:"
                                        )
                                    elif button_id == "btn_no_cliente":
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "¡Perfecto! Un asesor se pondrá en contacto contigo a la brevedad."
                                        )
                                    elif button_id.startswith("plan_"):
                                        # El usuario seleccionó un plan específico
                                        id_plan = button_id.split("_")[1]
                                        
                                        # Aquí aplicamos tu consulta exacta de cuotas
                                        try:
                                            conn = obtener_conexion_db()
                                            cursor = conn.cursor(dictionary=True)
                                            
                                            query_cuotas = """
                                                SELECT c.numcuota, c.fechavenc, c.fechapago, c.importe, c.estado, c.idcuota 
                                                FROM cuotas c 
                                                INNER JOIN altaplanafil apf ON c.idalta = apf.idalta 
                                                WHERE apf.idplan = %s 
                                                ORDER BY c.idcuota ASC
                                            """
                                            cursor.execute(query_cuotas, (id_plan,))
                                            cuotas = cursor.fetchall()
                                            
                                            cursor.close()
                                            conn.close()

                                            if cuotas:
                                                # Formateamos un resumen breve para enviar por WhatsApp
                                                mensaje_respuesta = f"*Estado de Cuotas - Plan {id_plan}:*\n\n"
                                                for c in cuotas[:5]: # Mostramos las primeras 5 pendientes/recientes
                                                    estado_txt = c['estado'] or 'Pendiente'
                                                    mensaje_respuesta += f"• Cuota {c['numcuota']}: ${c['importe']} (Venc: {c['fechavenc']}) - [{estado_txt}]\n"
                                                
                                                WhatsAppService.enviar_mensaje_texto(remitente, mensaje_respuesta)
                                            else:
                                                WhatsAppService.enviar_mensaje_texto(remitente, "No se registran cuotas para este plan.")
                                        except Exception as db_err:
                                            logging.error(f"Error consultando cuotas: {str(db_err)}")
                                            WhatsAppService.enviar_mensaje_texto(remitente, "Error al consultar las cuotas en el sistema.")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"Error procesando el webhook de WhatsApp: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7410, debug=False)