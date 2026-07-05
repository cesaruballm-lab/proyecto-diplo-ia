import os
import sys
import subprocess
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

# Resolver rutas del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRAPER_DIR = os.path.join(BASE_DIR, "scraper")

def run_scrapy_spider():
    """
    Ejecuta el Scrapy Spider en un proceso separado para evitar conflictos del reactor de Twisted.
    Devuelve un diccionario con el código de salida, stdout y stderr.
    """
    print("=== [Scheduler] Iniciando ejecución del Scraper BNA ===")
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "scrapy", "crawl", "bna_cotizaciones"],
            cwd=SCRAPER_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()
        return_code = process.returncode

        print(f"=== [Scheduler] Scraper finalizado con código: {return_code} ===")
        if return_code != 0:
            print(f"Error en Scraper stderr:\n{stderr}")

        return {
            "returncode": return_code,
            "stdout": stdout,
            "stderr": stderr
        }
    except Exception as e:
        err = str(e)
        print(f"Excepción al intentar ejecutar Scraper: {err}")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": err
        }

# Instancia global del planificador
scheduler = BackgroundScheduler()

def run_scrapy_spider_in_background():
    result = run_scrapy_spider()
    if result["returncode"] != 0:
        print(f"=== [Scheduler] Scraper error asíncrono: {result['stderr']}")


def trigger_scraping():
    """
    Dispara la ejecución del scraper de forma asíncrona en un hilo separado
    para no bloquear el thread principal de FastAPI.
    """
    thread = threading.Thread(target=run_scrapy_spider_in_background, daemon=True)
    thread.start()


def trigger_scraping_sync():
    """
    Ejecuta el scraper en el hilo actual y devuelve el resultado inmediatamente.
    """
    return run_scrapy_spider()

def init_scheduler(run_on_startup: bool = True):
    """
    Inicializa el planificador diario y ejecuta la carga inicial si corresponde.
    """
    tz = timezone('America/Argentina/Buenos_Aires')

    # Programar a las 18:00 todos los días
    scheduler.add_job(
        run_scrapy_spider,
        'cron',
        hour=18,
        minute=0,
        timezone=tz,
        id='bna_daily_scraper',
        replace_existing=True
    )

    scheduler.start()
    print("[Scheduler] APScheduler iniciado.")

    if run_on_startup:
        print("[Scheduler] Desencadenando scrapeo inicial al inicio...")
        trigger_scraping()
