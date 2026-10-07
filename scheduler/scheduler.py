from apscheduler.schedulers.background import BackgroundScheduler
from services.recordatorio_service import RecordatorioService

scheduler = BackgroundScheduler()

def init_scheduler(app):
    # Tarea programada: Se ejecuta diariamente a las 09:00 AM
    scheduler.add_job(
        func=RecordatorioService.procesar_envios_automaticos,
        trigger='cron',
        hour=9,
        minute=0,
        id='recordatorios_whatsapp_daily'
    )
    
    # Iniciar ejecutor de fondo sin bloquear Flask
    if not scheduler.running:
        scheduler.start()
        print("Scheduler de WhatsApp iniciado correctamente.")