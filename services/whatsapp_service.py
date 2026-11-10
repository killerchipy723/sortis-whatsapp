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
    def enviar_mensaje_texto(telefono: str, mensaje: str) -> dict:
        """Envía un mensaje de texto plano al usuario."""
        telefono_fmt = WhatsAppService.limpiar_telefono(telefono)
        url = f"https://graph.facebook.com/v19.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono_fmt,
            "type": "text",
            "text": {"body": mensaje}
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=12)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def enviar_menu_principal(telefono: str) -> dict:
        """Envía el menú principal con botones interactivos."""
        cuerpo = "¡Hola! Bienvenido a Sortis Motos. Selecciona una opción para continuar:"
        botones = [
            {"id": "btn_cliente", "title": "Soy cliente"},
            {"id": "btn_no_cliente", "title": "No soy cliente"}
        ]
        return WhatsAppService.enviar_menu_botones(telefono, cuerpo, botones)

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
                "name": "hello_world",
                "language": {"code": "en_US"}
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=12)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def enviar_recordatorio_plantilla(telefono: str, nombre: str, num_cuota: str, nombre_plan: str, fecha_venc: str, importe: str) -> dict:
        """Envía el recordatorio oficial usando la plantilla aprobada por Meta con 5 variables."""
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
                "language": {"code": "es_AR"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(nombre)},       # {{1}}
                            {"type": "text", "text": str(num_cuota)},    # {{2}}
                            {"type": "text", "text": str(nombre_plan)},  # {{3}}
                            {"type": "text", "text": str(fecha_venc)},   # {{4}}
                            {"type": "text", "text": str(importe)}       # {{5}}
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
    @staticmethod
    def enviar_menu_botones(telefono: str, cuerpo_mensaje: str, botones: list) -> dict:
        """
        Envía un mensaje interactivo con botones (máximo 3 botones).
        """
        telefono_fmt = WhatsAppService.limpiar_telefono(telefono)
        url = f"https://graph.facebook.com/v19.0/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        headers = {
            "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
        action_buttons = []
        for btn in botones[:3]:
            action_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn['id'],
                    "title": btn['title'][:20]
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": telefono_fmt,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": cuerpo_mensaje},
                "action": {"buttons": action_buttons}
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=12)
            return response.json()
        except Exception as e:
            return {"error": str(e)}