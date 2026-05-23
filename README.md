# BNA Exchange Monitor

Sistema integral de **extracción, almacenamiento y administración** de cotizaciones oficiales del Banco de la Nación Argentina (BNA) para Dólar U.S.A y Euro (billetes y divisas).

---

## 📋 Descripción General

Esta aplicación unifica en un único servicio Python:

- **Scraper automático** (Scrapy) que extrae las cotizaciones del BNA una vez por día.
- **API REST** (FastAPI) protegida por API Keys para que sistemas externos consulten las cotizaciones.
- **Panel de administración web** (HTML/CSS/JS) con login para gestionar cotizaciones, clientes y ver logs de auditoría.
- **Planificador embebido** (APScheduler) que ejecuta el scraper diariamente a las 18:00 hs (Argentina).

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                                                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Admin UI        │  │  API Pública │  │   Scheduler   │  │
│  │  /static/*.html  │  │  /api/v1/    │  │  APScheduler  │  │
│  └────────┬────────┘  └──────┬───────┘  └──────┬────────┘  │
│           │                  │                  │           │
│           └──────────────────▼──────────────────▼           │
│                        FastAPI Routers                      │
│                        + Middleware Auditoría               │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────▼───────────────┐
              │     Supabase (PostgreSQL)      │
              │  cotizaciones | api_keys       │
              │  api_logs                      │
              └───────────────────────────────┘
```

### Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Web Framework | FastAPI + Uvicorn |
| Scraper | Scrapy 2.x |
| Base de Datos | Supabase (PostgreSQL) |
| Scheduler | APScheduler 3.x |
| Autenticación Admin | JWT (PyJWT) vía cookie HTTP-only |
| Autenticación API | API Keys con hash SHA-256 |
| Frontend | HTML5 + Vanilla CSS + Vanilla JS |

---

## 📁 Estructura del Proyecto

```
proyecto-diplo-ia/
├── .env.example                    # Plantilla de variables de entorno
├── .env                            # Variables de entorno (no commitear)
├── requirements.txt                # Dependencias Python
├── supabase_schema.sql             # DDL para crear las tablas en Supabase
│
├── scraper/                        # Extractor Scrapy
│   ├── scrapy.cfg
│   └── bna_scraper/
│       ├── settings.py             # Configuración del crawler
│       ├── items.py                # Definición de ítems
│       ├── pipelines.py            # Persistencia en Supabase (upsert)
│       └── spiders/
│           └── bna_spider.py       # Lógica de extracción BNA
│
├── backend/                        # Servidor FastAPI
│   ├── main.py                     # Punto de entrada + middlewares
│   ├── database/
│   │   └── supabase_client.py      # Cliente de Supabase
│   ├── auth/
│   │   └── security.py             # JWT, hashing de API Keys SHA-256
│   ├── scheduler/
│   │   └── tasks.py                # APScheduler + ejecución del spider
│   ├── routers/
│   │   ├── admin.py                # CRUD admin + gestión API Keys + logs
│   │   └── public_api.py           # Endpoints para clientes externos
│   └── static/                     # Frontend embebido
│       ├── index.html              # Dashboard administrativo
│       ├── login.html              # Pantalla de login
│       ├── css/styles.css          # Estilos glassmorphism dark mode
│       └── js/app.js               # Lógica AJAX del panel
│
└── tests/
    ├── bna_mock.html               # HTML de prueba del sitio BNA
    └── output.json                 # Resultado del último test local
```

---

## 🗄️ Esquema de Base de Datos

### Tabla `cotizaciones`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único |
| `fecha_registro` | DATE | Fecha del día en que se guardó el registro (cubre feriados/fines de semana) |
| `fecha_oficial_bna` | DATE | Última fecha hábil informada por el BNA en la tabla |
| `hora_actualizacion` | VARCHAR | Hora de actualización informada por el BNA (ej: `"17:02"`) |
| `moneda` | VARCHAR | `"USD"` o `"EUR"` |
| `tipo` | VARCHAR | `"billete"` o `"divisa"` |
| `compra` | NUMERIC | Valor de compra |
| `venta` | NUMERIC | Valor de venta |
| `origen` | VARCHAR | `"scraped"` (automático) o `"manual"` (cargado desde el panel) |
| `creado_por` | VARCHAR | `"sistema"` si es automático, o el nombre del admin si es manual |

> **Clave única:** `(fecha_registro, moneda, tipo)` — garantiza un solo registro por moneda por día, evitando duplicados.

### Tabla `api_keys`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único |
| `cliente_nombre` | VARCHAR | Nombre del cliente o sistema |
| `cliente_email` | VARCHAR | Email de contacto |
| `api_key_hash` | VARCHAR | Hash SHA-256 de la API Key (nunca se guarda en texto plano) |
| `api_key_prefix` | VARCHAR | Prefijo visible para el admin (ej: `bna_live_a3b2`) |
| `activo` | BOOLEAN | `true` si tiene acceso, `false` si fue revocada |

### Tabla `api_logs`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único |
| `api_key_id` | UUID (FK) | Referencia al cliente que realizó la llamada |
| `endpoint` | VARCHAR | Endpoint consultado |
| `metodo` | VARCHAR | Método HTTP (`GET`, `POST`, etc.) |
| `ip_address` | VARCHAR | IP de origen |
| `status_code` | INTEGER | Código HTTP devuelto |
| `created_at` | TIMESTAMPTZ | Fecha y hora de la llamada |

---

## ⚙️ Instalación y Configuración

### 1. Clonar el repositorio y crear el entorno virtual

```bash
git clone https://github.com/tu-usuario/proyecto-diplo-ia.git
cd proyecto-diplo-ia

python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copiar el archivo de ejemplo y completar con los valores reales:

```bash
cp .env.example .env
```

```ini
# .env

SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-service-role-key-de-supabase

ADMIN_USERNAME=admin
ADMIN_PASSWORD=tu_contraseña_segura_aqui

JWT_SECRET_KEY=genera_una_clave_aleatoria_larga_aqui
```

> ⚠️ Usar la **Service Role Key** de Supabase (no la anon key), ya que el backend necesita permisos de escritura sin restricciones de RLS.

### 3. Crear las tablas en Supabase

1. Ingresar al panel de Supabase → **SQL Editor** → **New Query**
2. Pegar el contenido del archivo `supabase_schema.sql`
3. Ejecutar con **Run**

### 4. Iniciar el servidor

```bash
# Modo desarrollo (con recarga automática)
.\venv\Scripts\python -m uvicorn backend.main:app --reload

# Producción
.\venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

El servidor estará disponible en: **`http://localhost:8000`**

> 📌 Al iniciar, el scheduler ejecutará automáticamente un primer scrapeo del BNA y luego programará la ejecución diaria a las **18:00 hs (GMT-3)**.

---

## 🖥️ Panel de Administración

Acceder desde el navegador a `http://localhost:8000`. El sistema redirigirá al login automáticamente.

### Secciones disponibles:

| Sección | Descripción |
|---|---|
| **Cotizaciones** | Historial completo con filtros por moneda, tipo y fecha. Permite cargar, editar o eliminar registros manualmente. Botón para forzar el scrapeo del BNA en cualquier momento. |
| **API Keys Clientes** | Alta de nuevos clientes con generación de API Key (se muestra una sola vez). Revocación instantánea de acceso. |
| **Logs de Auditoría** | Registro de cada llamada a la API pública: cliente, IP, endpoint, código HTTP y timestamp. |

---

## 🔌 API Reference

### Autenticación

Todos los endpoints públicos requieren enviar el header:

```
X-API-Key: bna_live_tu_clave_aqui
```

Las API Keys se generan desde el panel de administración. Cada llamada (exitosa o fallida) queda registrada en los logs de auditoría.

---

### `GET /api/v1/cotizaciones`

Retorna el listado de cotizaciones almacenadas. Soporta filtros opcionales por fecha, moneda y tipo.

**Parámetros de query:**

| Parámetro | Tipo | Descripción | Ejemplo |
|---|---|---|---|
| `fecha` | `YYYY-MM-DD` | Fecha de registro (cubre fines de semana y feriados) | `2026-05-23` |
| `moneda` | `string` | Filtrar por moneda | `USD` o `EUR` |
| `tipo` | `string` | Filtrar por tipo de cotización | `billete` o `divisa` |

#### Ejemplos cURL

**Obtener todas las cotizaciones:**
```bash
curl -X GET "http://localhost:8000/api/v1/cotizaciones" \
  -H "X-API-Key: bna_live_tu_clave_aqui"
```

**Obtener cotizaciones de una fecha específica:**
```bash
curl -X GET "http://localhost:8000/api/v1/cotizaciones?fecha=2026-05-23" \
  -H "X-API-Key: bna_live_tu_clave_aqui"
```

**Filtrar solo el dólar billete:**
```bash
curl -X GET "http://localhost:8000/api/v1/cotizaciones?moneda=USD&tipo=billete" \
  -H "X-API-Key: bna_live_tu_clave_aqui"
```

**Filtrar euro divisa de una fecha puntual:**
```bash
curl -X GET "http://localhost:8000/api/v1/cotizaciones?fecha=2026-05-23&moneda=EUR&tipo=divisa" \
  -H "X-API-Key: bna_live_tu_clave_aqui"
```

**Respuesta exitosa (200 OK):**
```json
[
  {
    "id": "8f2a1b3c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "fecha_registro": "2026-05-23",
    "fecha_oficial_bna": "2026-05-23",
    "hora_actualizacion": "17:02",
    "moneda": "USD",
    "tipo": "billete",
    "compra": 1375.0,
    "venta": 1425.0,
    "origen": "scraped"
  },
  {
    "id": "9a3b2c1d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "fecha_registro": "2026-05-23",
    "fecha_oficial_bna": "2026-05-23",
    "hora_actualizacion": "17:02",
    "moneda": "USD",
    "tipo": "divisa",
    "compra": 1394.0,
    "venta": 1403.0,
    "origen": "scraped"
  }
]
```

**Respuesta sin API Key (401 Unauthorized):**
```json
{
  "detail": "Cabecera X-API-Key ausente."
}
```

**Respuesta con API Key inválida (401 Unauthorized):**
```json
{
  "detail": "API Key inválida."
}
```

**Respuesta con API Key revocada (403 Forbidden):**
```json
{
  "detail": "API Key revocada o inactiva."
}
```

---

### Cobertura de fines de semana y feriados

Si se consulta una cotización para un día donde el BNA no opera (sábado, domingo, feriado), el sistema devuelve el registro correspondiente a ese día calendario, cuya `fecha_oficial_bna` apuntará al último día hábil anterior.

**Ejemplo — consulta de un sábado:**
```bash
curl -X GET "http://localhost:8000/api/v1/cotizaciones?fecha=2026-05-24" \
  -H "X-API-Key: bna_live_tu_clave_aqui"
```

```json
[
  {
    "fecha_registro": "2026-05-24",
    "fecha_oficial_bna": "2026-05-22",
    "hora_actualizacion": "17:02",
    "moneda": "USD",
    "tipo": "billete",
    "compra": 1375.0,
    "venta": 1425.0,
    "origen": "scraped"
  }
]
```

> `fecha_registro` es el sábado 24 (día buscado), `fecha_oficial_bna` es el viernes 22 (último día que el BNA actualizó).

---

## 🕷️ Extracción (Scraper)

El spider extrae los datos desde `https://www.bna.com.ar/Personas` procesando dos tablas:

| Tabla BNA | Selector CSS | Formato numérico |
|---|---|---|
| Cotización Billetes | `#billetes tbody tr` | Formato AR: `1.375,00` (punto de miles, coma decimal) |
| Cotización Divisas | `#divisas tbody tr` | Formato EN: `1394.0000` (punto decimal) |

Las monedas filtradas son **únicamente** `"Dolar U.S.A"` y `"Euro"`. Otras monedas de la tabla (Real, Libra, Dólar Canadiense, Dólar Australiano) son ignoradas.

### Ejecutar el scraper manualmente (sin el servidor)

```bash
cd scraper

# Scrapeo real del BNA
..\venv\Scripts\scrapy crawl bna_cotizaciones

# Test con archivo HTML local
..\venv\Scripts\scrapy crawl bna_cotizaciones \
  -a start_urls="file:///ruta/al/proyecto/tests/bna_mock.html" \
  -O ../tests/output.json
```

---

## 🔐 Seguridad

- Las **API Keys** nunca se almacenan en texto plano. Solo se guarda su hash SHA-256. La clave completa se muestra **una única vez** al momento de generarla.
- Las sesiones del administrador se manejan con **tokens JWT** almacenados en cookies HTTP-only de corta duración (2 horas).
- El **middleware de auditoría** intercepta y registra cada llamada a `/api/v1/` incluyendo intentos fallidos de autenticación.

---
