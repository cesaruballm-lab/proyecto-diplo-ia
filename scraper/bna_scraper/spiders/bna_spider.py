import scrapy
from datetime import datetime

class BnaCotizacionesSpider(scrapy.Spider):
    name = "bna_cotizaciones"
    allowed_domains = ["bna.com.ar"]
    start_urls = ["https://www.bna.com.ar/Personas"]

    # Podemos configurar User-Agent y otras configuraciones en settings o directamente como settings de la spider
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    def __init__(self, start_urls=None, *args, **kwargs):
        super(BnaCotizacionesSpider, self).__init__(*args, **kwargs)
        if start_urls:
            self.start_urls = [start_urls]

    def parse(self, response):
        # 1. Extraer metadatos comunes de Billetes
        fecha_billetes_raw = response.css('#billetes th.fechaCot::text').get()
        fecha_oficial_billetes = None
        if fecha_billetes_raw:
            try:
                fecha_oficial_billetes = datetime.strptime(fecha_billetes_raw.strip(), "%d/%m/%Y").date()
            except ValueError:
                self.logger.error(f"No se pudo parsear fecha de billetes: {fecha_billetes_raw}")

        hora_raw = response.css('#billetes div.legal::text').re_first(r'Hora Actualización:\s*(\d{2}:\d{2})')
        hora_actualizacion = hora_raw.strip() if hora_raw else "00:00"

        # 2. Extraer metadatos comunes de Divisas
        fecha_divisas_raw = response.css('#divisas th.fechaCot::text').get()
        fecha_oficial_divisas = None
        if fecha_divisas_raw:
            try:
                fecha_oficial_divisas = datetime.strptime(fecha_divisas_raw.strip(), "%d/%m/%Y").date()
            except ValueError:
                self.logger.error(f"No se pudo parsear fecha de divisas: {fecha_divisas_raw}")

        # Si no encontramos fecha, usamos el día de hoy como respaldo
        if not fecha_oficial_billetes:
            fecha_oficial_billetes = datetime.now().date()
        if not fecha_oficial_divisas:
            fecha_oficial_divisas = fecha_oficial_billetes

        # 3. Procesar Billetes
        for row in response.css('#billetes tbody tr'):
            moneda_raw = row.css('td.tit::text').get()
            if not moneda_raw:
                continue
            
            moneda_clean = moneda_raw.strip()
            moneda = None
            if "Dolar U.S.A" in moneda_clean:
                moneda = "USD"
            elif "Euro" in moneda_clean:
                moneda = "EUR"

            if moneda:
                compra_raw = row.css('td:nth-child(2)::text').get()
                venta_raw = row.css('td:nth-child(3)::text').get()
                if compra_raw and venta_raw:
                    try:
                        # Billetes usan formato AR: 1.375,00 → quitar punto de miles, coma a decimal
                        compra = float(compra_raw.strip().replace('.', '').replace(',', '.'))
                        venta = float(venta_raw.strip().replace('.', '').replace(',', '.'))
                        yield {
                            "fecha_oficial_bna": fecha_oficial_billetes.strftime("%Y-%m-%d"),
                            "hora_actualizacion": hora_actualizacion,
                            "moneda": moneda,
                            "tipo": "billete",
                            "compra": compra,
                            "venta": venta
                        }
                    except ValueError as e:
                        self.logger.error(f"Error al convertir valores de billetes para {moneda}: {e}")

        # 4. Procesar Divisas
        for row in response.css('#divisas tbody tr'):
            moneda_raw = row.css('td.tit::text').get()
            if not moneda_raw:
                continue
            
            moneda_clean = moneda_raw.strip()
            moneda = None
            if "Dolar U.S.A" in moneda_clean:
                moneda = "USD"
            elif "Euro" in moneda_clean:
                moneda = "EUR"

            if moneda:
                compra_raw = row.css('td:nth-child(2)::text').get()
                venta_raw = row.css('td:nth-child(3)::text').get()
                if compra_raw and venta_raw:
                    try:
                        # Divisas usan formato EN: 1394.0000 → el punto ya es el decimal, solo reemplazar coma por punto si existiera
                        compra = float(compra_raw.strip().replace(',', '.'))
                        venta = float(venta_raw.strip().replace(',', '.'))
                        yield {
                            "fecha_oficial_bna": fecha_oficial_divisas.strftime("%Y-%m-%d"),
                            "hora_actualizacion": hora_actualizacion,  # Se hereda la hora de billetes
                            "moneda": moneda,
                            "tipo": "divisa",
                            "compra": compra,
                            "venta": venta
                        }
                    except ValueError as e:
                        self.logger.error(f"Error al convertir valores de divisas para {moneda}: {e}")
