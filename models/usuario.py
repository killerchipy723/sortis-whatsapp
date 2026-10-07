from database.connection import get_db

class UsuarioModel:
    @staticmethod
    def autenticar(username, password):
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT * FROM usuarios 
                    WHERE usuario = %s AND clave = %s AND estado = 'Activo'
                """
                cursor.execute(sql, (username, password))
                return cursor.fetchone()
        finally:
            conn.close()