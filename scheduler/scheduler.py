from apscheduler.schedulers.background import BackgroundScheduler
from services.recordatorio_service import RecordatorioService
import atexit

def iniciar_scheduler(app): # <--- Pasamos 'app' como parámetro
    scheduler = BackgroundScheduler()
    
    # Función intermedia que inyecta el contexto de Flask
    def tarea_diaria_con_contexto():
        with app.app_context():
            print("⏰ [Scheduler] Ejecutando tarea automática de recordatorios...")
            try:
                RecordatorioService.procesar_envios_automaticos()
                print("✅ [Scheduler] Tarea finalizada con éxito.")
            except Exception as e:
                print(f"❌ [Scheduler Error] Falló la tarea automática: {str(e)}")

    scheduler.add_job(
        func=tarea_diaria_con_contexto,
        trigger="cron",
        hour=9,
        minute=40
    )
    
    scheduler.start()
    print("⏰ [Scheduler] Iniciado correctamente en segundo plano.")
    
    # Apagar el scheduler de manera limpia al salir
    atexit.register(lambda: scheduler.shutdown())