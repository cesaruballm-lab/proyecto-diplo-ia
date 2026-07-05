import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

from backend.database.supabase_client import supabase
from backend.auth.security import hash_provided_key, verify_admin_token
from backend.scheduler.tasks import init_scheduler, scheduler
from backend.routers import admin, public_api

# --- Lógica de Auditoría en Hilos Auxiliares (Non-blocking) ---

def verify_api_key_in_db(api_key_hash: str):
    """
    Busca la API Key en Supabase (ejecución sincrónica para threadpool).
    """
    try:
        res = supabase.table("api_keys") \
            .select("id, cliente_nombre, activo") \
            .eq("api_key_hash", api_key_hash) \
            .execute()
        return res.data
    except Exception as e:
        print(f"[Middleware Error] Error consultando API Key: {e}")
        return None

def write_api_log_to_db(api_key_id: str, endpoint: str, metodo: str, ip_address: str, status_code: int):
    """
    Guarda el log de auditoría en Supabase (ejecución sincrónica para threadpool).
    """
    try:
        supabase.table("api_logs").insert({
            "api_key_id": api_key_id,
            "endpoint": endpoint,
            "metodo": metodo,
            "ip_address": ip_address,
            "status_code": status_code
        }).execute()
    except Exception as e:
        print(f"[Middleware Error] Error escribiendo en api_logs: {e}")

# --- Manejador de Ciclo de Vida ---

def should_enable_scheduler() -> bool:
    """Determina si el scheduler debe arrancar en este entorno."""
    # En Vercel, no hay garantía de que el proceso se mantenga vivo.
    if os.getenv("VERCEL"):
        return False
    return os.getenv("ENABLE_SCHEDULER", "true").lower() in ("1", "true", "yes")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_enabled = should_enable_scheduler()
    scheduler_running = False

    if scheduler_enabled:
        init_scheduler(run_on_startup=True)
        scheduler_running = True
    else:
        print("[Scheduler] Scheduler deshabilitado en este entorno.")

    yield

    if scheduler_running:
        scheduler.shutdown()

# --- Configuración de la App ---

app = FastAPI(
    title="BNA exchange rates API & Admin",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Middleware de Auditoría y Validación de API Key ---

@app.middleware("http")
async def audit_and_auth_middleware(request: Request, call_next):
    # Solo intercepta rutas de API pública de clientes (/api/v1/)
    if not request.url.path.startswith("/api/v1"):
        return await call_next(request)

    ip_address = request.client.host if request.client else "unknown"
    metodo = request.method
    endpoint = request.url.path

    # 1. Obtener API Key
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Cabecera X-API-Key ausente."}
        )
        # Loguear intento fallido sin API Key
        await run_in_threadpool(write_api_log_to_db, None, endpoint, metodo, ip_address, 401)
        return response

    # 2. Hashear y Validar contra Supabase usando threadpool
    api_key_hash = hash_provided_key(api_key)
    db_keys = await run_in_threadpool(verify_api_key_in_db, api_key_hash)

    if db_keys is None:
        # Error al conectar con la base de datos
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error de comunicación con el servicio de base de datos."}
        )

    if not db_keys:
        response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "API Key inválida."}
        )
        await run_in_threadpool(write_api_log_to_db, None, endpoint, metodo, ip_address, 401)
        return response

    key_record = db_keys[0]
    api_key_id = key_record.get("id")

    # 3. Comprobar si la API Key está activa
    if not key_record.get("activo", False):
        response = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "API Key revocada o inactiva."}
        )
        await run_in_threadpool(write_api_log_to_db, api_key_id, endpoint, metodo, ip_address, 403)
        return response

    # Proseguir con la petición
    response = await call_next(request)

    # 4. Registrar log exitoso/respuesta final en segundo plano
    await run_in_threadpool(write_api_log_to_db, api_key_id, endpoint, metodo, ip_address, response.status_code)

    return response

# --- Inclusión de Routers ---

app.include_router(public_api.router)
app.include_router(admin.router)

# --- Rutas de Frontend Estático y Control de Acceso ---

# Asegura que la carpeta static exista
os.makedirs("backend/static", exist_ok=True)

# Servir archivos estáticos
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

@app.get("/")
def read_root(request: Request):
    """
    Ruta raíz. Si está autenticado, sirve el Dashboard; de lo contrario, redirige al Login.
    """
    token = request.cookies.get("admin_session")
    if not token or not verify_admin_token(token):
        return RedirectResponse(url="/login")
    return FileResponse("backend/static/index.html")

@app.get("/login")
def login_page(request: Request):
    """
    Página de Login. Si ya hay sesión iniciada, redirige al Dashboard.
    """
    token = request.cookies.get("admin_session")
    if token and verify_admin_token(token):
        return RedirectResponse(url="/")
    return FileResponse("backend/static/login.html")
