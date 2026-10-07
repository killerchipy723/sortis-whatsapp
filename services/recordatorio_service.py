from datetime import datetime, timedelta
from database.connection import get_db
from services.whatsapp_service import WhatsAppService

class RecordatorioService:
    
    @staticmethod
    def obtener_cuotas_por_vencer(dias_anticipacion=3):
        """
        Obtiene las cuotas sin pagar que vencen dentro de `dias_anticipacion` días 
        y no tienen un envío exitoso registrado hoy.
        """
        fecha_target = (datetime.now() + timedelta(days=dias_anticipacion)).strftime('%Y-%m-%d')
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        c.idcuota,
                        c.numcuota,
                        c.fechavenc,
                        c.importe,
                        a.idafiliado,
                        a.apenomb,
                        a.telefono
                    FROM cuotas c
                    JOIN altaplanafil ap ON c.idalta = ap.idalta
                    JOIN afiliado a ON ap.idafiliado = a.idafiliado
                    LEFT JOIN envios_whatsapp ew 
                           ON ew.idcuota = c.idcuota 
                          AND ew.estado = 'ENVIADO' 
                          AND DATE(ew.fecha_envio) = CURDATE()
                    WHERE c.estado != 'Pagado'
                      AND DATE(c.fechavenc) = %s
                      AND a.telefono IS NOT NULL AND a.telefono != ''
                      AND ew.idenvio IS NULL;
                """
                cursor.execute(sql, (fecha_target,))
                return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def registrar_envio(idcuota, idafiliado, telefono, mensaje, estado, respuesta_api):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO envios_whatsapp 
                    (idcuota, idafiliado, telefono, mensaje, estado, respuesta_api)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    idcuota, idafiliado, telefono, mensaje, estado, str(respuesta_api)
                ))
        finally:
            conn.close()

    @staticmethod
    def procesar_envios_automaticos():
        """Metodo invocado por el Scheduler"""
        cuotas = RecordatorioService.obtener_cuotas_por_vencer(dias_anticipacion=3)
        print(f"[{datetime.now()}] Procesando recordatorios. Cuotas a notificar: {len(cuotas)}")

        for item in cuotas:
            # Formatear la fecha a DD/MM/YYYY
            fecha_venc = item['fechavenc'].strftime('%d/%m/%Y') if hasattr(item['fechavenc'], 'strftime') else str(item['fechavenc'])
            importe_fmt = f"{item['importe']:,.0f}".replace(",", ".")

            # Mensaje tal como lo solicitaste
            mensaje = (
                f"Hola {item['apenomb']} 👋\n"
                f"Le recordamos que tiene pendiente la cuota N.º {item['numcuota']} correspondiente a su plan.\n"
                f"📅 Vencimiento: {fecha_venc}\n\n"
                f"💰 Importe: ${importe_fmt}\n"
                f"Si ya realizó el pago, por favor desestime este mensaje."
            )

            # Enviar por WhatsApp API
            res = WhatsAppService.enviar_mensaje_texto(item['telefono'], mensaje)
            
            # Evaluar respuesta de Meta
            if 'messages' in res:
                estado = 'ENVIADO'
            else:
                estado = 'FALLIDO'

            # Registrar en la base de datos
            RecordatorioService.registrar_envio(
                idcuota=item['idcuota'],
                idafiliado=item['idafiliado'],
                telefono=item['telefono'],
                mensaje=mensaje,
                estado=estado,
                respuesta_api=res
            )