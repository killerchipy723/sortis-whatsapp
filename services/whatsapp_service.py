import re
import requests
from config import Config

class WhatsAppService:
    @staticmethod
    def limpiar_telefono(telefono: str) -> str:
        """Limpia el teléfono para formato internacional (ej. 5493876123456)."""
        if not telefono:
            return ""
        
        num = re.sub(r'\D', '', str(telefono))
        if num.startswith('0'):
            num = num[1:]
        if len(num) == 10:
            num = "549" + num
            
        return num

    @staticmethod
    def enviar_hello_world(telefono: str) -> dict:
        """Prueba de envío usando la plantilla por defecto de Meta."""
        telefono_fmt = WhatsAppService.limpiar_telefono(telefono)
        url = f"https://graph.facebook.com/v19.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono_fmt,
            "type": "template",
            "template": {
                "name": "recordatorio_cuota_sortis",
                "language": {"code": "en_US"}
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=12)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def enviar_recordatorio_plantilla(telefono: str, nombre: str, num_cuota: str, fecha_venc: str, importe: str) -> dict:
        telefono_fmt = WhatsAppService.limpiar_telefono(telefono)
        url = f"https://graph.facebook.com/v19.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono_fmt,
            "type": "template",
            "template": {
                "name": "recordatorio_cuota_sortis",
                "language": {"code": "es"},  # Cambiar a 'es_AR' si en Meta la creaste como Español (Argentina)
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(nombre)},
                            {"type": "text", "text": str(num_cuota)},
                            {"type": "text", "text": str(fecha_venc)},
                            {"type": "text", "text": str(importe)}
                        ]
                    }
                ]
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=12)
            return response.json()
        except Exception as e:
            return {"error": str(e)}