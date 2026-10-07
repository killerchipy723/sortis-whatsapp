import pymysql
# Sintaxis compatible con DBUtils 3.0+
from dbutils.pooled_db import PooledDB
from config import Config

pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    host=Config.DB_HOST,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    database=Config.DB_NAME,
    port=Config.DB_PORT,
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True
)

def get_db():
    return pool.connection()