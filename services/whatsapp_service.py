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
                        a.telefono,
                        ap.idalta
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
                conn.commit()
        finally:
            conn.close()

    @staticmethod   
    def procesar_envios_automaticos():
        """Método invocado por el Scheduler"""
        cuotas = RecordatorioService.obtener_cuotas_por_vencer(dias_anticipacion=3)
        print(f"[{datetime.now()}] Procesando recordatorios. Cuotas a notificar: {len(cuotas)}")

        for c in cuotas:
            # Formatear fecha e importe
            fecha_venc = c['fechavenc'].strftime('%d/%m/%Y') if hasattr(c['fechavenc'], 'strftime') else str(c['fechavenc'])
            importe_fmt = f"{c['importe']:,.0f}".replace(",", ".")

            # Enviar utilizando la plantilla oficial aprobada por Meta
            res = WhatsAppService.enviar_recordatorio_plantilla(
                telefono=c['telefono'],
                nombre=c['apenomb'],
                num_cuota=str(c['numcuota']),
                fecha_venc=fecha_venc,
                importe=importe_fmt
            )
            
            # Evaluar respuesta de Meta
            estado = 'ENVIADO' if 'messages' in res else 'FALLIDO'

            # Registrar el envío en la base de datos
            mensaje_log = f"Plantilla recordatorio_cuota_sortis - Cuota {c['numcuota']}"
            RecordatorioService.registrar_envio(
                idcuota=c['idcuota'],
                idafiliado=c['idafiliado'],
                telefono=c['telefono'],
                mensaje=mensaje_log,
                estado=estado,
                respuesta_api=res
            )