import os
import logging
import time
from datetime import date
from werkzeug.utils import secure_filename
import mysql.connector
from flask import Flask, request, jsonify, render_template, url_for, redirect, flash, session
from services.whatsapp_service import WhatsAppService
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler
from services.recordatorio_service import RecordatorioService 
from scheduler import iniciar_scheduler
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

app.secret_key = 'sortis_motos_key_secreta_2026'
VERIFY_TOKEN = "sortis_motos_token_seguro"

# Directorios para subida de imágenes de planes y ganadores
UPLOAD_FOLDER_PLANES = 'static/img/planes'
UPLOAD_FOLDER_GANADORES = 'static/img/ganadores'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER_PLANES'] = UPLOAD_FOLDER_PLANES
app.config['UPLOAD_FOLDER_GANADORES'] = UPLOAD_FOLDER_GANADORES

os.makedirs(UPLOAD_FOLDER_PLANES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_GANADORES, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Diccionario para gestionar sesiones de WhatsApp en memoria
USER_SESSIONS = {}
TIMEOUT_SESION = 600  # 10 minutos

def obtener_o_crear_sesion(remitente):
    ahora = time.time()
    if remitente in USER_SESSIONS:
        sesion = USER_SESSIONS[remitente]
        if ahora - sesion.get("ultimo_tiempo", 0) > TIMEOUT_SESION:
            USER_SESSIONS[remitente] = {"estado": "INICIO", "ultimo_tiempo": ahora}
        else:
            sesion["ultimo_tiempo"] = ahora
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

# =========================================================
# 1. RUTA PRINCIPAL: LANDING PAGE COMERCIAL (PÚBLICA)
# =========================================================
@app.route("/")
def landing():
    conn = None
    cursor = None
    planes = []
    ganadores = []
    noticias = []
    
    try:
        conn = obtener_conexion_db()
        cursor = conn.cursor(dictionary=True)
        
        # Consultar planes (asegúrate de tener la columna 'imagen' en tu tabla plan)
        cursor.execute("SELECT * FROM plan")
        planes = cursor.fetchall()
        
        # Consultar novedades y ganadores (si creaste la tabla novedades_web)
        try:
            cursor.execute("SELECT * FROM novedades_web ORDER BY fecha_creacion DESC")
            novedades = cursor.fetchall()
            ganadores = [n for n in novedades if n['tipo'] == 'GANADOR']
            noticias = [n for n in novedades if n['tipo'] == 'NOTICIA']
        except Exception:
            # Si la tabla novedades_web todavía no fue creada en MySQL, evitamos que rompa la app
            pass
            
    except Exception as e:
        print(f"Error al cargar la landing page: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('landing.html', planes=planes, ganadores=ganadores, noticias=noticias)

# =========================================================
# 2. RUTA DE LOGIN (ACCESO PARA CLIENTES)
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    error_mensaje = None
    
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
                    error_mensaje = "DNI no encontrado. Recuerda que tu contraseña es tu número de DNI."
                    
            except Exception as e:
                print(f"Error en el login: {str(e)}")
                error_mensaje = "Ocurrió un error al intentar conectar con la base de datos."
                
            finally:
                if cursor: cursor.close()
                if conn: conn.close()

    return render_template('login.html', error=error_mensaje)

# =========================================================
# 3. RUTA DEL INDEX (PANEL PRINCIPAL POST-LOGIN)
# =========================================================
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
        
        # 2. Consultar el catálogo real de planes
        query_planes = "SELECT idplan, nombreplan, descripcion, cantcuotas, importe FROM plan"
        cursor.execute(query_planes)
        planes = cursor.fetchall()
        
    except Exception as e:
        print(f"Error al cargar el dashboard: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
        
    return render_template('index.html', cuotas=cuotas, planes=planes)

# =========================================================
# 4. RUTA PARA SUBIR/ACTUALIZAR IMAGEN DE UN PLAN (ADMIN)
# =========================================================
@app.route('/admin/plan/imagen/<int:idplan>', methods=['POST'])
def actualizar_imagen_plan(idplan):
    if 'imagen' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('landing'))
        
    file = request.files['imagen']
    if file and allowed_file(file.filename):
        filename = secure_filename(f"plan_{idplan}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER_PLANES'], filename))
        
        conn = None
        cursor = None
        try:
            conn = obtener_conexion_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE plan SET imagen = %s WHERE idplan = %s", (filename, idplan))
            conn.commit()
            flash('Imagen del plan actualizada correctamente', 'success')
        except Exception as e:
            print(f"Error al actualizar imagen: {e}")
            flash('Error al guardar la imagen en la base de datos', 'danger')
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
    return redirect(url_for('landing'))

# =========================================================
# 5. CERRAR SESIÓN
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('landing')) # Al salir, lo devolvemos a la landing page pública


# =========================================================
# PANEL DE ADMINISTRACIÓN (GESTIÓN DE GANADORES Y NOTICIAS)
# =========================================================

# 1. Ruta de Login para el Administrador (puedes usar una clave fija o verificar en BD)
@app.route("/admin/login", methods=["GET", "POST"])
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        clave = request.form.get("password")
        # Definí aquí tu contraseña de administrador secreta
        if clave == "sortis2026admin": 
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Contraseña de administrador incorrecta.", "danger")
            
    return render_template('admin_login.html')

# 2. Dashboard Principal del Admin
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Debes iniciar sesión como administrador.", "warning")
        return redirect(url_for('admin_login'))
        
    conn = obtener_conexion_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM novedades_web ORDER BY fecha_creacion DESC")
        elementos = cursor.fetchall()
    except Exception as e:
        print(f"Error al cargar admin: {e}")
        elementos = []
    finally:
        cursor.close()
        conn.close()
        
    return render_template('admin_dashboard.html', elementos=elementos)

# 3. Guardar Nuevo Ganador o Noticia
@app.route("/admin/guardar", methods=["POST"])
def admin_guardar():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
        
    tipo = request.form.get("tipo") # 'GANADOR' o 'NOTICIA'
    titulo = request.form.get("titulo")
    subtitulo = request.form.get("subtitulo")
    file = request.files.get("imagen")
    
    filename = "default.jpg"
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{tipo.lower()}_{int(time.time())}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER_GANADORES'], filename))
        
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO novedades_web (tipo, titulo, subtitulo, imagen) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (tipo, titulo, subtitulo, filename))
        conn.commit()
        flash("Registro guardado y publicado correctamente.", "success")
    except Exception as e:
        print(f"Error al insertar: {e}")
        flash("Error al guardar en la base de datos.", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

# 4. Eliminar Ganador o Noticia
@app.route("/admin/eliminar/<int:id>", methods=["POST"])
def admin_eliminar(id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
        
    conn = obtener_conexion_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM novedades_web WHERE id = %s", (id,))
        conn.commit()
        flash("Elemento eliminado correctamente.", "info")
    except Exception as e:
        print(f"Error al eliminar: {e}")
        flash("No se pudo eliminar el elemento.", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_dashboard'))

# 5. Cerrar sesión de Admin
@app.route("/admin/logout")
def admin_logout():
    session.pop('is_admin', None)
    flash("Sesión de administrador cerrada.", "info")
    return redirect(url_for('landing'))

# =========================================================
# GESTION DE CLIENTES
# =========================================================


@app.route("/api/inscribir", methods=["POST"])
def procesar_inscripcion_virtual():
    # Recibimos todos los datos del modal de la Landing Page
    # Forzamos el nombre en mayúsculas por seguridad
    nombre = request.form.get("nombre", "").strip().upper()
    dni = request.form.get("dni", "").strip()
    cuil = request.form.get("cuil", "").strip()
    domicilio = request.form.get("domicilio", "").strip()
    telefono = request.form.get("telefono", "").strip()
    idplan = request.form.get("idplan")
    acepta_contrato = request.form.get("contrato") # Validación del contrato
    
    # Validar aceptación de términos
    if not acepta_contrato or acepta_contrato != "on":
        return jsonify({"success": False, "message": "Debes aceptar los términos del contrato de adjudicación para continuar."})
    
    conn = obtener_conexion_db()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # PASO 1: Verificar si el afiliado ya existe por su DNI
        cursor.execute("SELECT idafiliado FROM afiliado WHERE dni = %s LIMIT 1", (dni,))
        afiliado = cursor.fetchone()
        
        if afiliado:
            id_afiliado = afiliado['idafiliado']
        else:
            # Si no existe, lo registramos automáticamente en la tabla afiliado con todos sus datos
            # (idvendedor = 1 asume un vendedor genérico web/online por defecto)
            query_afiliado = """
                INSERT INTO afiliado (apenomb, dni, cuil, domicilio, telefono, estado, idvendedor) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_afiliado, (nombre, dni, cuil, domicilio, telefono, "Activo", 1))
            conn.commit()
            id_afiliado = cursor.lastrowid
            
        # PASO 2: Verificar si ya tiene este plan activo para evitar duplicados
        cursor.execute("SELECT COUNT(*) AS total FROM altaplanafil WHERE idafiliado = %s AND idplan = %s", (id_afiliado, idplan))
        if cursor.fetchone()['total'] > 0:
            return jsonify({"success": False, "message": "Ya te encuentras inscripto en este plan."})
            
        # PASO 3: Obtener importe y cantidad de cuotas del plan
        cursor.execute("SELECT importe, cantcuotas FROM plan WHERE idplan = %s", (idplan,))
        plan = cursor.fetchone()
        
        if not plan:
            return jsonify({"success": False, "message": "El plan seleccionado no existe."})
            
        importe_plan = plan['importe']
        cant_cuotas = plan['cantcuotas']
        
        # PASO 4: Dar de alta el plan en altaplanafil
        fecha_alta = date.today()
        fecha_cobro = fecha_alta + relativedelta(months=1) # Primer vencimiento al mes siguiente
        
        query_alta = """
            INSERT INTO altaplanafil (idafiliado, idplan, idvendedor, fechalta, fechacobro, importe, estado) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_alta, (id_afiliado, idplan, 1, fecha_alta, fecha_cobro, importe_plan, "Pendiente"))
        conn.commit()
        id_alta = cursor.lastrowid
        
        # PASO 5: Generar las cuotas automáticamente mes a mes
        fecha_vencimiento = fecha_cobro
        for num_cuota in range(1, cant_cuotas + 1):
            query_cuota = """
                INSERT INTO cuotas (idalta, numcuota, fechavenc, fechapago, importe, estado, obs) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_cuota, (
                id_alta, 
                num_cuota, 
                fecha_vencimiento, 
                None, 
                importe_plan, 
                "Pendiente", 
                "Inscripción Web Virtual"
            ))
            conn.commit()
            fecha_vencimiento = fecha_vencimiento + relativedelta(months=1)
            
        return jsonify({"success": True, "message": "¡Inscripción registrada con éxito! Generando contrato..."})
        
    except Exception as e:
        print(f"Error en inscripción: {str(e)}")
        return jsonify({"success": False, "message": "Ocurrió un error al procesar la alta en el sistema."})
    finally:
        cursor.close()
        conn.close()

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