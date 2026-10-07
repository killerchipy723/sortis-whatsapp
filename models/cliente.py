from database.connection import get_db

class ClienteModel:
    @staticmethod
    def buscar_por_dni(dni):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        altaplanafil.idafiliado,
                        plan.idplan,
                        afiliado.apenomb AS afiliado,
                        afiliado.dni,
                        plan.nombreplan AS plan,
                        plan.cantcuotas,
                        altaplanafil.fechacobro AS fecha_alta,
                        altaplanafil.estado
                    FROM altaplanafil
                    JOIN afiliado ON afiliado.idafiliado = altaplanafil.idafiliado
                    JOIN plan ON plan.idplan = altaplanafil.idplan
                    WHERE afiliado.dni = %s
                """
                cursor.execute(sql, (dni,))
                return cursor.fetchall()
        finally:
            conn.close()