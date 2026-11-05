from services.whatsapp_service import WhatsAppService
from database.connection import get_db

class BotService:

    @staticmethod
    def manejar_mensaje_entrante(telefono: str, texto_usuario: str, button_id: str = None):
        """
        Controla el flujo de la conversación según lo que el usuario presione o escriba.
        """
        # Si el usuario hace clic en los botones principales del inicio
        if button_id == "btn_soy_cliente":
            WhatsAppService.enviar_mensaje_texto(
                telefono, 
                "¡Perfecto! 📝 Por favor, ingresá tu número de DNI (sin puntos) para que podamos encontrarte en el sistema:"
            )
            # Aquí podrías guardar temporalmente en memoria o base de datos que este teléfono está esperando un DNI
            return

        elif button_id == "btn_no_soy_cliente":
            WhatsAppService.enviar_mensaje_texto(
                telefono, 
                "¡Bienvenido a *Sortis Motos*! 🏍️ Contanos, ¿estás interesado en algún modelo en particular o querés conocer nuestros planes de financiación?"
            )
            return

        # Si el usuario tipeó algo (por ejemplo, su DNI)
        if texto_usuario.isdigit() and len(texto_usuario) >= 7:
            BotService.verificar_dni_cliente(telefono, texto_usuario)
            return
        
        # Si no es un DNI ni un botón, enviamos el menú principal de bienvenida
        BotService.enviar_bienvenida_inicial(telefono)

    @staticmethod
    def enviar_bienvenida_inicial(telefono: str):
        """Envía el saludo inicial con los dos botones principales."""
        saludo = "¡Hola! Nos da gusto que estés aquí en *Sortis Motos*. Seleccioná una de las siguientes opciones:"
        botones = [
            {"id": "btn_soy_cliente", "title": "Soy cliente"},
            {"id": "btn_no_soy_cliente", "title": "No soy cliente"}
        ]
        WhatsAppService.enviar_menu_botones(telefono, saludo, botones)

    @staticmethod
    def verificar_dni_cliente(telefono: str, dni: str):
        """Busca al afiliado en MySQL por su DNI para validar que exista."""
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                # Asumiendo que tu tabla afiliado tiene un campo 'dni' o similar
                sql = "SELECT idafiliado, apenomb FROM afiliado WHERE dni = %s OR nrodoc = %s LIMIT 1"
                cursor.execute(sql, (dni, dni))
                cliente = cursor.fetchone()

                if cliente:
                    # Opcional: Actualizar el teléfono del cliente si no lo tenía registrado
                    WhatsAppService.enviar_mensaje_texto(
                        telefono, 
                        f"¡Hola {cliente['apenomb']}! 👋 Te hemos reconocido con éxito en el sistema. ¿Qué te gustaría consultar hoy?"
                    )
                    # Acá podrías desplegar su menú de cuentas y cuotas pendientes
                else:
                    WhatsAppService.enviar_mensaje_texto(
                        telefono, 
                        "No pudimos encontrar un registro con ese DNI en nuestras bases de datos. Por favor, verificá que esté bien escrito o comunicate con un asesor."
                    )
        finally:
            conn.close()