import os

import os

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import date
from backend.database.supabase_client import supabase
from backend.auth.security import (
    get_current_admin,
    create_admin_token,
    generate_new_api_key,
    ADMIN_USERNAME,
    ADMIN_PASSWORD
)

router = APIRouter(
    prefix="/api/admin",
    tags=["API Administrativa Panel"]
)

# --- Esquemas Pydantic ---

class LoginPayload(BaseModel):
    username: str
    password: str

class CotizacionCreate(BaseModel):
    fecha_registro: date = Field(default_factory=date.today)
    fecha_oficial_bna: date
    hora_actualizacion: str = Field(..., max_length=10)
    moneda: str = Field(..., CHECK="moneda in ['USD', 'EUR']")
    tipo: str = Field(..., CHECK="tipo in ['billete', 'divisa']")
    compra: float
    venta: float

class CotizacionUpdate(BaseModel):
    fecha_oficial_bna: Optional[date] = None
    hora_actualizacion: Optional[str] = None
    compra: float
    venta: float

class ApiKeyCreate(BaseModel):
    cliente_nombre: str = Field(..., min_length=2, max_length=150)
    cliente_email: EmailStr

# --- Rutas ---

# 1. Login
@router.post("/login")
def login(payload: LoginPayload, response: Response):
    if payload.username == ADMIN_USERNAME and payload.password == ADMIN_PASSWORD:
        token = create_access_token_or_similar = create_admin_token()
        # Set cookie secure=False para desarrollo local HTTP, httponly=True por seguridad
        response.set_cookie(
            key="admin_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=120 * 60  # 2 horas
        )
        return {"status": "success", "message": "Autenticación exitosa"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contraseña incorrectos."
    )

# 2. Logout
@router.post("/logout")
def logout(response: Response, username: str = Depends(get_current_admin)):
    response.delete_cookie(key="admin_session")
    return {"status": "success", "message": "Sesión cerrada"}

# 3. Listar Cotizaciones (Vista Admin Completa)
@router.get("/cotizaciones")
def list_cotizaciones(username: str = Depends(get_current_admin)):
    try:
        res = supabase.table("cotizaciones") \
            .select("*") \
            .order("fecha_registro", desc=True) \
            .order("moneda") \
            .execute()
        return res.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar cotizaciones: {str(e)}"
        )

# 4. Crear Cotización Manual
@router.post("/cotizaciones")
def create_cotizacion(payload: CotizacionCreate, username: str = Depends(get_current_admin)):
    # Normalizar valores
    moneda = payload.moneda.upper().strip()
    tipo = payload.tipo.lower().strip()

    if moneda not in ["USD", "EUR"] or tipo not in ["billete", "divisa"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Moneda o tipo de cotización inválidos."
        )

    data = {
        "fecha_registro": str(payload.fecha_registro),
        "fecha_oficial_bna": str(payload.fecha_oficial_bna),
        "hora_actualizacion": payload.hora_actualizacion.strip(),
        "moneda": moneda,
        "tipo": tipo,
        "compra": payload.compra,
        "venta": payload.venta,
        "origen": "manual",
        "creado_por": username
    }

    try:
        res = supabase.table("cotizaciones").upsert(
            data,
            on_conflict="fecha_registro,moneda,tipo"
        ).execute()
        return {"status": "success", "data": res.data[0]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar cotización manual: {str(e)}"
        )

# 5. Editar Cotización
@router.put("/cotizaciones/{id}")
def update_cotizacion(id: str, payload: CotizacionUpdate, username: str = Depends(get_current_admin)):
    data = {
        "compra": payload.compra,
        "venta": payload.venta,
        "origen": "manual",
        "creado_por": username
    }
    if payload.fecha_oficial_bna:
        data["fecha_oficial_bna"] = str(payload.fecha_oficial_bna)
    if payload.hora_actualizacion:
        data["hora_actualizacion"] = payload.hora_actualizacion.strip()

    try:
        res = supabase.table("cotizaciones").update(data).eq("id", id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Cotización no encontrada.")
        return {"status": "success", "data": res.data[0]}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al editar cotización: {str(e)}"
        )

# 6. Eliminar Cotización
@router.delete("/cotizaciones/{id}")
def delete_cotizacion(id: str, username: str = Depends(get_current_admin)):
    try:
        res = supabase.table("cotizaciones").delete().eq("id", id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Cotización no encontrada.")
        return {"status": "success", "message": "Cotización eliminada correctamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar cotización: {str(e)}"
        )

# 7. Listar Clientes y API Keys
@router.get("/api-keys")
def list_api_keys(username: str = Depends(get_current_admin)):
    try:
        res = supabase.table("api_keys") \
            .select("id, cliente_nombre, cliente_email, api_key_prefix, activo, created_at") \
            .order("created_at", desc=True) \
            .execute()
        return res.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar API Keys: {str(e)}"
        )

# 8. Crear API Key (Cliente Nuevo)
@router.post("/api-keys")
def create_api_key_endpoint(payload: ApiKeyCreate, username: str = Depends(get_current_admin)):
    full_key, prefix, api_key_hash = generate_new_api_key()

    data = {
        "cliente_nombre": payload.cliente_nombre.strip(),
        "cliente_email": payload.cliente_email.strip(),
        "api_key_hash": api_key_hash,
        "api_key_prefix": prefix,
        "activo": True
    }

    try:
        supabase.table("api_keys").insert(data).execute()
        # Se retorna la clave completa solo en este momento
        return {
            "status": "success",
            "api_key_completa": full_key,
            "prefix": prefix,
            "cliente_nombre": payload.cliente_nombre
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar la API Key: {str(e)}"
        )

# 9. Revocar API Key (Desactivar)
@router.delete("/api-keys/{id}")
def revoke_api_key(id: str, username: str = Depends(get_current_admin)):
    try:
        # En lugar de eliminar físicamente, marcamos activo = False para conservar logs de auditoría
        res = supabase.table("api_keys").update({"activo": False}).eq("id", id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="API Key no encontrada.")
        return {"status": "success", "message": "API Key revocada correctamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al revocar la API Key: {str(e)}"
        )

# 10. Listar Logs de Auditoría
@router.get("/logs")
def list_logs(username: str = Depends(get_current_admin)):
    try:
        # Traer los logs con los campos del cliente correspondientes
        res = supabase.table("api_logs") \
            .select("id, endpoint, metodo, ip_address, status_code, created_at, api_keys(cliente_nombre, cliente_email)") \
            .order("created_at", desc=True) \
            .limit(100) \
            .execute()
        return res.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar logs de auditoría: {str(e)}"
        )

# 11. Disparar Scraper Manualmente
@router.post("/scrape/trigger")
def trigger_scrape(request: Request):
    from backend.scheduler.tasks import trigger_scraping_sync

    cron_token = request.headers.get("X-Cron-Token") or request.query_params.get("cron_token")
    configured_cron_token = os.getenv("CRON_TRIGGER_TOKEN")
    is_cron_call = bool(cron_token and configured_cron_token and cron_token == configured_cron_token)
    is_admin_call = False

    try:
        get_current_admin(request)
        is_admin_call = True
    except HTTPException:
        is_admin_call = False

    if not (is_admin_call or is_cron_call):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado. Se requiere sesión administrativa o token de cron válido."
        )

    try:
        result = trigger_scraping_sync()
        if result["returncode"] != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al ejecutar el scraper: {result['stderr'] or 'Sin salida de error.'}",
            )

        return {
            "status": "success",
            "message": "Scraper ejecutado y completado.",
            "stdout": result["stdout"],
            "stderr": result["stderr"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al disparar el scraper: {str(e)}"
        )
