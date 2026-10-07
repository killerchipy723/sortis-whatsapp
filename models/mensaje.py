from database.connection import get_db

class CuotaModel:
    @staticmethod
    def get_cuotas_por_afiliado_y_plan(idafiliado, idplan):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT c.idcuota, c.numcuota, c.fechavenc, c.fechapago, c.importe, c.estado
                    FROM cuotas c
                    INNER JOIN altaplanafil apf ON c.idalta = apf.idalta
                    WHERE apf.idafiliado = %s AND apf.idplan = %s
                    ORDER BY c.idcuota ASC
                """
                cursor.execute(sql, (idafiliado, idplan))
                return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_por_id(id_cuota):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM cuotas WHERE idcuota = %s"
                cursor.execute(sql, (id_cuota,))
                return cursor.fetchone()
        finally:
            conn.close()

    @staticmethod
    def actualizar_cuota(idcuota, importe, formapago, nrecibo, fechapago, idvendedor, obs, estado):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    UPDATE cuotas 
                    SET importe = %s, formapago = %s, nrecibo = %s, fechapago = %s, idvendedor = %s, obs = %s, estado = %s
                    WHERE idcuota = %s
                """
                affected_rows = cursor.execute(sql, (
                    importe, formapago, nrecibo, fechapago, idvendedor, obs, estado, idcuota
                ))
                return affected_rows > 0
        finally:
            conn.close()

    @staticmethod
    def obtener_detalle_recibo(id_cuota):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT c.idcuota, a.apenomb, c.numcuota, c.estado, c.obs, c.fechavenc, c.importe, c.fechapago 
                    FROM cuotas c 
                    JOIN altaplanafil ap ON c.idalta = ap.idalta 
                    JOIN afiliado a ON ap.idafiliado = a.idafiliado 
                    WHERE c.idcuota = %s
                """
                cursor.execute(sql, (id_cuota,))
                return cursor.fetchone()
        finally:
            conn.close()