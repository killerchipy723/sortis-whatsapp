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

        # Diccionario para agrupar cuotas por cliente (idafiliado)
        clientes_agrupados = {}
        for item in cuotas:
            id_cli = item['idafiliado']
            if id_cli not in clientes_agrupados:
                clientes_agrupados[id_cli] = {
                    'apenomb': item['apenomb'],
                    'telefono': item['telefono'],
                    'cuotas': []
                }
            clientes_agrupados[id_cli]['cuotas'].append(item)

        # Iterar por cada cliente consolidando sus planes/cuotas
        for id_cli, datos in clientes_agrupados.items():
            
            detalle_cuotas_texto = ""
            total_importe = 0
            
            for c in datos['cuotas']:
                fecha_venc = c['fechavenc'].strftime('%d/%m/%Y') if hasattr(c['fechavenc'], 'strftime') else str(c['fechavenc'])
                importe_fmt = f"{c['importe']:,.0f}".replace(",", ".")
                detalle_cuotas_texto += f"• Cuota N.º {c['numcuota']} (Venc: {fecha_venc}) - ${importe_fmt}\n"
                total_importe += float(c['importe'])

            total_importe_fmt = f"{total_importe:,.0f}".replace(",", ".")

            # Mensaje unificado que contempla uno o varios planes
            mensaje = (
                f"Hola {datos['apenomb']} 👋\n"
                f"Le recordamos que tiene los siguientes vencimientos pendientes en sus planes de Sortis Motos:\n\n"
                f"{detalle_cuotas_texto}\n"
                f"💰 **Total a abonar: ${total_importe_fmt}**\n\n"
                f"Si ya realizó el pago, por favor desestime este mensaje."
            )

            # Enviar por WhatsApp API (Usando tu método de envío actual)
            res = WhatsAppService.enviar_mensaje_texto(datos['telefono'], mensaje)
            
            # Evaluar respuesta de Meta
            estado = 'ENVIADO' if 'messages' in res else 'FALLIDO'

            # Registrar el envío de cada cuota procesada individualmente
            for c in datos['cuotas']:
                RecordatorioService.registrar_envio(
                    idcuota=c['idcuota'],
                    idafiliado=id_cli,
                    telefono=datos['telefono'],
                    mensaje=mensaje,
                    estado=estado,
                    respuesta_api=res
                )