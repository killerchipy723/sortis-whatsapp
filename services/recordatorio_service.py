from datetime import datetime, timedelta
from database.connection import get_db
from services.whatsapp_service import WhatsAppService

class RecordatorioService:
    
    @staticmethod
    def obtener_cuotas_por_vencer(dias_anticipacion=3):
        fecha_target = (datetime.now() + timedelta(days=dias_anticipacion)).strftime('%Y-%m-%d')
        conn = get_db()
        try:
            # CORREGIDO: Se remueve dictionary=True para evitar el error de SteadyDB
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        c.idcuota,
                        c.numcuota,
                        c.fechavenc,
                        COALESCE(NULLIF(c.importe, 0), p.importe, 0) AS importe,
                        a.idafiliado,
                        a.apenomb,
                        a.telefono,
                        p.idplan,
                        p.nombreplan
                    FROM cuotas c
                    JOIN altaplanafil ap ON c.idalta = ap.idalta
                    JOIN afiliado a ON ap.idafiliado = a.idafiliado
                    JOIN plan p ON ap.idplan = p.idplan
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

        for item in cuotas:
            # 1. Proteger la fecha
            if item.get('fechavenc'):
                fecha_venc = item['fechavenc'].strftime('%d/%m/%Y') if hasattr(item['fechavenc'], 'strftime') else str(item['fechavenc'])
            else:
                fecha_venc = "Sin fecha"

            # 2. Gestionar el importe asegurando que nunca sea 0 si el plan tiene precio
            importe_val = item.get('importe')
            if importe_val is not None and importe_val > 0:
                importe_fmt = f"${importe_val:,.0f}".replace(",", ".")
            else:
                importe_fmt = "A confirmar"

            nombre_cliente = item.get('apenomb', 'Cliente')
            num_cuota = str(item.get('numcuota', 'N/A'))
            nombre_plan = str(item.get('nombreplan', 'General'))

            # Mensaje de respaldo (para guardar en la tabla envios_whatsapp)
            mensaje_log = (
                f"¡Hola, {nombre_cliente}! Te recordamos que la cuota N.º {num_cuota} correspondiente al plan {nombre_plan} "
                f"vence en 3 días ({fecha_venc}). El monto pendiente es de {importe_fmt}. "
                f"Si ya realizaste el pago, por favor desestimá este mensaje."
            )

            # Enviar usando la plantilla oficial con los 5 parámetros
            res = WhatsAppService.enviar_recordatorio_plantilla(
                telefono=item['telefono'],
                nombre=nombre_cliente,
                num_cuota=num_cuota,
                nombre_plan=nombre_plan,
                fecha_venc=fecha_venc,
                importe=importe_fmt
            )
            
            # Evaluar respuesta de Meta
            if isinstance(res, dict) and 'messages' in res:
                estado = 'ENVIADO'
            else:
                estado = 'FALLIDO'
                print(f"⚠️ Error enviando WhatsApp a {item['telefono']}: {res}")

            # Registrar en la base de datos
            RecordatorioService.registrar_envio(
                idcuota=item['idcuota'],
                idafiliado=item['idafiliado'],
                telefono=item['telefono'],
                mensaje=mensaje_log,
                estado=estado,
                respuesta_api=res
            )