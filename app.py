import logging
import time
from datetime import date
import mysql.connector
from flask import Flask, request, jsonify,render_template,url_for,Request,redirect,flash,session
from services.whatsapp_service import WhatsAppService
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler
from services.recordatorio_service import RecordatorioService  # Ajusta la ruta según tu estructura
from scheduler import iniciar_scheduler

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

app.secret_key = 'sortis_motos_key_secreta_2026'
VERIFY_TOKEN = "sortis_motos_token_seguro"

# Diccionario para gestionar el estado y la sesión de cada usuario en memoria
# Estructura: { remitente: { "estado": "...", "ultimo_tiempo": timestamp, "dni": "...", "id_afiliado": "..." } }
USER_SESSIONS = {}
TIMEOUT_SESION = 600  # 10 minutos de inactividad en segundos (10 * 60)

def obtener_o_crear_sesion(remitente):
    """Obtiene la sesión del usuario, validando si expiró por inactividad."""
    ahora = time.time()
    if remitente in USER_SESSIONS:
        sesion = USER_SESSIONS[remitente]
        # Si pasó el tiempo límite de inactividad, reiniciamos la sesión
        if ahora - sesion.get("ultimo_tiempo", 0) > TIMEOUT_SESION:
            USER_SESSIONS[remitente] = {"estado": "INICIO", "ultimo_tiempo": ahora}
        else:
            sesion["ultimo_tiempo"] = ahora  # Actualizamos el timestamp de actividad
    else:
        USER_SESSIONS[remitente] = {"estado": "INICIO", "ultimo_tiempo": ahora}
    return USER_SESSIONS[remitente]

def obtener_conexion_db():
    """Establece conexión con la base de datos MySQL."""
    return mysql.connector.connect(
        host=getattr(Config, 'DB_HOST', 'localhost'),
        user=getattr(Config, 'DB_USER', 'tu_usuario'),
        password=getattr(Config, 'DB_PASSWORD', 'tu_contraseña'),
        database=getattr(Config, 'DB_NAME', 'sortis_motos')
    )

# --- RUTA DE LOGIN (Página principal) ---
@app.route("/", methods=["GET", "POST"])
def login():
    error_mensaje = None # Variable para el mensaje de error directo
    
    if request.method == "POST":
        password_ingresada = request.form.get("password")
        
        if not password_ingresada or not password_ingresada.isdigit():
            error_mensaje = "Por favor, ingresa un número de DNI válido (solo números)."
        else:
            conn = None
            cursor = None
            try:
                conn = obtener_conexion_db()
                cursor = conn.cursor(dictionary=True)
                
                query = "SELECT idafiliado, apenomb, dni FROM afiliado WHERE dni = %s LIMIT 1"
                cursor.execute(query, (password_ingresada,))
                afiliado = cursor.fetchone()
                
                if afiliado:
                    session['user_id'] = afiliado['idafiliado']
                    session['user_name'] = afiliado['apenomb']
                    session['user_dni'] = afiliado['dni']
                    return redirect(url_for('index'))
                else:
                    # Mensaje claro y directo cuando el DNI no existe
                    error_mensaje = "DNI no encontrado. Recuerda que tu contraseña es tu número de DNI."
                    
            except Exception as e:
                print(f"Error en el login: {str(e)}")
                error_mensaje = "Ocurrió un error al intentar conectar con la base de datos."
                
            finally:
                if cursor: cursor.close()
                if conn: conn.close()

    # Le pasamos la variable 'error' a la plantilla
    return render_template('login.html', error=error_mensaje)

# --- RUTA DEL INDEX (Panel principal post-login) ---
@app.route("/index")
def index():
    if 'user_id' not in session:
        flash("Por favor, inicia sesión primero.", "warning")
        return redirect(url_for('login'))
        
    idafiliado = session['user_id']
    
    conn = None
    cursor = None
    cuotas = []
    planes = []
    
    try:
        conn = obtener_conexion_db()
        cursor = conn.cursor(dictionary=True)
        
        # 1. Consultar cuotas reales del afiliado logueado
        query_cuotas = """
            SELECT c.idcuota, c.numcuota, c.fechavenc, c.fechapago, 
                   COALESCE(NULLIF(c.importe, 0), p.importe, 0) AS importe, 
                   c.estado, p.nombreplan
            FROM cuotas c
            JOIN altaplanafil ap ON c.idalta = ap.idalta
            JOIN plan p ON ap.idplan = p.idplan
            WHERE ap.idafiliado = %s
            ORDER BY c.numcuota ASC
        """
        cursor.execute(query_cuotas, (idafiliado,))
        cuotas = cursor.fetchall()
        
        # 2. Consultar el catálogo real de planes desde la tabla plan
        query_planes = "SELECT idplan, nombreplan, descripcion, cantcuotas, importe FROM plan"
        cursor.execute(query_planes)
        planes = cursor.fetchall()
        
    except Exception as e:
        print(f"Error al cargar el dashboard: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('index.html', cuotas=cuotas, planes=planes)

# ----------------- CERRAR SESSION --------------------------------------
@app.route("/logout")
def logout():
    # Limpiamos todas las variables de la sesión
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('login'))


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
                            sesion = obtener_o_crear_sesion(remitente)
                            
                            # 1. Manejo de Mensajes de Texto según el estado actual
                            if "text" in message:
                                texto_ingresado = message["text"]["body"].strip()
                                texto_lower = texto_ingresado.lower()
                                logging.info(f"Texto de {remitente} [Estado: {sesion['estado']}]: {texto_ingresado}")
                                
                                # Comando global para volver al inicio en cualquier momento
                                if texto_lower in ["hola", "menu", "volver", "0"]:
                                    sesion["estado"] = "INICIO"
                                    WhatsAppService.enviar_menu_principal(remitente)
                                    continue

                                # Estado: Esperando que el usuario ingrese su DNI
                                if sesion["estado"] == "ESPERANDO_DNI":
                                    if texto_ingresado.isdigit() and 7 <= len(texto_ingresado) <= 8:
                                        dni = texto_ingresado
                                        try:
                                            conn = obtener_conexion_db()
                                            cursor = conn.cursor(dictionary=True)
                                            
                                            query_afiliado = """
                                                SELECT idafiliado, apenomb 
                                                FROM afiliado
                                                WHERE dni = %s
                                            """
                                            cursor.execute(query_afiliado, (dni,))
                                            afiliado = cursor.fetchone()
                                            
                                            cursor.close()
                                            conn.close()

                                            if afiliado:
                                                sesion["dni"] = dni
                                                sesion["id_afiliado"] = afiliado['idafiliado']
                                                sesion["estado"] = "VERIFICANDO_IDENTIDAD"
                                                
                                                nombre_cliente = afiliado['apenomb']
                                                botones_verificacion = [
                                                    {"id": "verif_si", "title": "Sí, soy yo"},
                                                    {"id": "verif_no", "title": "No soy yo"}
                                                ]
                                                WhatsAppService.enviar_menu_botones(
                                                    remitente,
                                                    f"Hemos encontrado una cuenta con el DNI ingresado. ¿Pertenece a *{nombre_cliente}*?",
                                                    botones_verificacion
                                                )
                                            else:
                                                WhatsAppService.enviar_mensaje_texto(
                                                    remitente, 
                                                    "No encontramos registros con ese DNI. Verifica el número o escribe *Volver* para ir al menú."
                                                )
                                        except Exception as db_err:
                                            logging.error(f"Error de base de datos: {str(db_err)}")
                                            WhatsAppService.enviar_mensaje_texto(remitente, "Ocurrió un error al consultar tus datos.")
                                    else:
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "Por favor, ingresa un número de DNI válido (7 u 8 dígitos) o escribe *Volver*."
                                        )
                                else:
                                    # Si escribe texto aleatorio fuera de un flujo activo, le mostramos el menú principal
                                    sesion["estado"] = "INICIO"
                                    WhatsAppService.enviar_menu_principal(remitente)

                            # 2. Respuestas a Botones Interactivos
                            elif "interactive" in message:
                                interactive = message["interactive"]
                                if interactive.get("type") == "button_reply":
                                    button_id = interactive["button_reply"]["id"]
                                    logging.info(f"Botón presionado por {remitente}: {button_id}")

                                    if button_id == "btn_cliente":
                                        sesion["estado"] = "ESPERANDO_DNI"
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "Por favor, ingresa tu número de DNI para validar tu cuenta:"
                                        )
                                    elif button_id == "btn_no_cliente":
                                        sesion["estado"] = "INICIO"
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "¡Perfecto! Un asesor se pondrá en contacto contigo a la brevedad."
                                        )
                                    
                                    # Paso A: Confirma identidad (Sí, soy yo) -> Listar planes
                                    elif button_id == "verif_si":
                                        id_afiliado = sesion.get("id_afiliado")
                                        if not id_afiliado:
                                            WhatsAppService.enviar_mensaje_texto(remitente, "La sesión expiró. Escribe *Hola* para comenzar de nuevo.")
                                            sesion["estado"] = "INICIO"
                                            continue

                                        try:
                                            conn = obtener_conexion_db()
                                            cursor = conn.cursor(dictionary=True)
                                            
                                            query_planes = """
                                                SELECT apf.idplan, p.nombreplan, a.apenomb 
                                                FROM altaplanafil apf
                                                INNER JOIN afiliado a ON apf.idafiliado = a.idafiliado
                                                INNER JOIN plan p ON apf.idplan = p.idplan
                                                WHERE a.idafiliado = %s
                                            """
                                            cursor.execute(query_planes, (id_afiliado,))
                                            planes = cursor.fetchall()
                                            
                                            cursor.close()
                                            conn.close()

                                            if planes:
                                                sesion["estado"] = "SELECCIONANDO_PLAN"
                                                nombre_cliente = planes[0]['apenomb']
                                                detalle_msj = f"📋 *Detalle de planes encontrados:*\n"
                                                detalle_msj += f"• *Cliente:* {nombre_cliente}\n\n"
                                                detalle_msj += f"Selecciona el plan que deseas consultar:"

                                                botones_planes = []
                                                for p in planes[:3]: # Máximo 3 botones en WhatsApp
                                                    id_plan_str = str(p['idplan'])
                                                    nombre_plan = p['nombreplan'] or f"Plan {id_plan_str}"
                                                    botones_planes.append({
                                                        "id": f"plan_{id_plan_str}",
                                                        "title": nombre_plan[:20]
                                                    })
                                                
                                                WhatsAppService.enviar_menu_botones(remitente, detalle_msj, botones_planes)
                                            else:
                                                WhatsAppService.enviar_mensaje_texto(remitente, "No se encontraron planes inscriptos para este cliente.")
                                                sesion["estado"] = "INICIO"
                                        except Exception as db_err:
                                            logging.error(f"Error al buscar planes: {str(db_err)}")
                                            WhatsAppService.enviar_mensaje_texto(remitente, "Error al consultar los planes en el sistema.")

                                    # Paso B: Indica que NO es su identidad
                                    elif button_id == "verif_no":
                                        sesion["estado"] = "ESPERANDO_DNI"
                                        WhatsAppService.enviar_mensaje_texto(
                                            remitente, 
                                            "Entendido. Por favor, vuelve a ingresar tu número de DNI correcto:"
                                        )

                                    # Paso C: Selecciona un plan -> Resumen inteligente de cuotas estilo NetBeans
                                    elif button_id.startswith("plan_"):
                                        id_plan = button_id.split("_")[1]
                                        id_afiliado = sesion.get("id_afiliado")

                                        if not id_afiliado:
                                            WhatsAppService.enviar_mensaje_texto(remitente, "La sesión expiró. Escribe *Hola* para comenzar.")
                                            sesion["estado"] = "INICIO"
                                            continue
                                        
                                        try:
                                            conn = obtener_conexion_db()
                                            cursor = conn.cursor(dictionary=True)
                                            
                                            query_cuotas = """
                                                SELECT c.numcuota, c.fechavenc, c.fechapago, c.importe, c.estado, c.idcuota 
                                                FROM cuotas c 
                                                INNER JOIN altaplanafil apf ON c.idalta = apf.idalta 
                                                WHERE apf.idafiliado = %s AND apf.idplan = %s 
                                                ORDER BY c.idcuota ASC
                                            """
                                            cursor.execute(query_cuotas, (id_afiliado, id_plan))
                                            cuotas = cursor.fetchall()
                                            
                                            cursor.close()
                                            conn.close()

                                            if cuotas:
                                                hoy = date.today()
                                                total_cuotas = len(cuotas)
                                                pagadas = 0
                                                restantes = 0
                                                con_atraso = 0

                                                for c in cuotas:
                                                    estado_db = (c['estado'] or "").strip().lower()
                                                    fechavenc = c['fechavenc']
                                                    fechapago = c['fechapago']

                                                    if fechapago is not None or estado_db in ["pagada", "pagado"]:
                                                        pagadas += 1
                                                    else:
                                                        restantes += 1
                                                        if fechavenc and fechavenc < hoy:
                                                            con_atraso += 1

                                                mensaje_respuesta = f"📊 *Resumen de Estado del Plan {id_plan}*\n\n"
                                                mensaje_respuesta += f"• *Total de cuotas:* {total_cuotas}\n"
                                                mensaje_respuesta += f"• *Pagadas:* {pagadas}\n"
                                                mensaje_respuesta += f"• *Restantes (Pendientes):* {restantes}\n"
                                                mensaje_respuesta += f"• *Con atraso (Vencidas):* {con_atraso}\n\n"

                                                if con_atraso >= 2:
                                                    mensaje_respuesta += "⚠️ *Estado:* Situación crítica - Posee múltiples cuotas vencidas.\n\n"
                                                elif con_atraso == 1:
                                                    mensaje_respuesta += "⚠️ *Estado:* Atraso - 1 cuota impaga vencida.\n\n"
                                                else:
                                                    mensaje_respuesta += "✅ *Estado:* Situación correcta al día.\n\n"

                                                mensaje_respuesta += "💡 *Escribe 'Hola' o 'Volver' cuando deseas realizar otra consulta.*"

                                                # Finalizamos el ciclo de consulta dejando al usuario libre (no se buclea)
                                                sesion["estado"] = "FINALIZADO"
                                                WhatsAppService.enviar_mensaje_texto(remitente, mensaje_respuesta)
                                            else:
                                                WhatsAppService.enviar_mensaje_texto(remitente, "No se registran cuotas para este plan.")
                                                sesion["estado"] = "INICIO"
                                        except Exception as db_err:
                                            logging.error(f"Error consultando cuotas: {str(db_err)}")
                                            WhatsAppService.enviar_mensaje_texto(remitente, "Error al consultar las cuotas en el sistema.")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"Error procesando el webhook de WhatsApp: {str(e)}")
        return jsonify({"error": str(e)}), 500

#--------------------------------------Envio de mensajes de whatsapp Diarios----------------------------------------
def tarea_diaria_recordatorios():
    with app.app_context():
        logging.info("Ejecutando tarea automática de recordatorios de cuotas...")
        try:
            RecordatorioService.procesar_envios_automaticos()
            logging.info("Tarea de recordatorios finalizada con éxito.")
        except Exception as e:
            logging.error(f"Error en la tarea automática de recordatorios: {str(e)}")

# Inicializar el BackgroundScheduler
scheduler = BackgroundScheduler()
# Configura la hora en que deseas que se envíe todos los días (ej. a las 09:00 horas)
scheduler.add_job(func=tarea_diaria_recordatorios, trigger="cron", hour=9, minute=0)
scheduler.start()

# Asegurarse de apagar el scheduler limpiamente al cerrar la app
import atexit
atexit.register(lambda: scheduler.shutdown())


# ----------------- mensajes enviados -----------------------
from database.connection import get_db
from flask import render_template

@app.route('/mensajes-enviados')
def mensajes_enviados():
    db = get_db()
    try:
        # Abrimos el cursor sin parámetros (compatible con SteadyDB)
        with db.cursor() as cursor:
            sql = """
                SELECT 
                    e.idenvio,
                    e.idcuota,
                    e.telefono,
                    e.mensaje,
                    e.estado,
                    e.fecha_envio,
                    a.apenomb
                FROM envios_whatsapp e
                LEFT JOIN afiliado a ON e.idafiliado = a.idafiliado
                ORDER BY e.fecha_envio DESC
            """
            cursor.execute(sql)
            mensajes = cursor.fetchall()
    finally:
        db.close()
        
    return render_template('mensajes_enviados.html', mensajes=mensajes)


if __name__ == '__main__':
    iniciar_scheduler(app) # Iniciamos el cron pasándole app
    app.run(host='0.0.0.0', port=7410, debug=True)