from services.whatsapp_service import WhatsAppService

# Cambia este número por tu celular personal para recibir la prueba
NUMERO_PRUEBA = "3876502243"  # O el número al que quieras enviar el test

print("Enviando mensaje de prueba via WhatsApp API...")

# Llamada a la plantilla que registraste
respuesta = WhatsAppService.enviar_recordatorio_plantilla(
    telefono=NUMERO_PRUEBA,
    nombre="Juan Perez",
    num_cuota="05",
    fecha_venc="10/10/2026",
    importe="15.000,00"
)

print("Respuesta de Meta API:")
print(respuesta)