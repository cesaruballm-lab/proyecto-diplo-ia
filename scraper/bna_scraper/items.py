import scrapy

class CotizacionItem(scrapy.Item):
    fecha_oficial_bna = scrapy.Field()
    hora_actualizacion = scrapy.Field()
    moneda = scrapy.Field()
    tipo = scrapy.Field()
    compra = scrapy.Field()
    venta = scrapy.Field()
