import os
from dotenv import load_dotenv

# Carga las variables del archivo .env
load_dotenv()

class Config:
    # Configuración de Base de Datos
    DB_HOST = os.getenv('DB_HOST', '200.58.106.156')
    DB_USER = os.getenv('DB_USER', 'c2710325_killer')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'SistemaIES6021')
    DB_NAME = os.getenv('DB_NAME', 'c2710325_sortis')
    DB_PORT = int(os.getenv('DB_PORT', 3306))

    # Configuración de WhatsApp Cloud API
    WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN', '')
    WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')