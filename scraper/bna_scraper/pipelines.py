import os
import pytz
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

class SupabasePipeline:
    def __init__(self):
        # Cargar variables de entorno
        load_dotenv()
        self.supabase_url = os.environ.get("SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_KEY")
        self.client = None

    def open_spider(self, spider):
        if not self.supabase_url or not self.supabase_key:
            spider.logger.error("Credenciales de Supabase no encontradas en el entorno.")
            return
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            spider.logger.info("Conexión con Supabase establecida en el Pipeline de Scrapy.")
        except Exception as e:
            spider.logger.error(f"Error de conexión con Supabase en Pipeline: {e}")

    def process_item(self, item, spider):
        if not self.client:
            spider.logger.error("El cliente de Supabase no está inicializado. Omitiendo guardado.")
            return item

        # Obtener fecha de hoy en la zona horaria de Argentina
        tz = pytz.timezone('America/Argentina/Buenos_Aires')
        fecha_registro = datetime.now(tz).date().strftime("%Y-%m-%d")

        data = {
            "fecha_registro": fecha_registro,
            "fecha_oficial_bna": item["fecha_oficial_bna"],
            "hora_actualizacion": item["hora_actualizacion"],
            "moneda": item["moneda"],
            "tipo": item["tipo"],
            "compra": item["compra"],
            "venta": item["venta"],
            "origen": "scraped",
            "creado_por": "sistema"
        }

        try:
            # Se realiza upsert en base a la clave de unicidad para evitar duplicados y actualizar si cambia
            self.client.table("cotizaciones").upsert(
                data,
                on_conflict="fecha_registro,moneda,tipo"
            ).execute()
            spider.logger.info(f"Datos insertados/actualizados en Supabase: {item['moneda']} {item['tipo']}")
        except Exception as e:
            spider.logger.error(f"Error al insertar en Supabase: {e}")

        return item
