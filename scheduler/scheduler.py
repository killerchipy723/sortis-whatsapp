from apscheduler.schedulers.background import BackgroundScheduler
from services.recordatorio_service import RecordatorioService
import atexit

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    
    # Configurar para que se ejecute todos los días a las 09:00 AM
    scheduler.add_job(
        func=RecordatorioService.procesar_envios_automaticos,
        trigger="cron",
        hour=9,
        minute=0
    )

    scheduler.start()
    print("⏰ [Scheduler] Iniciado correctamente en segundo plano.")

    # Detener limpiamente al cerrar la app
    atexit.register(lambda: scheduler.shutdown())