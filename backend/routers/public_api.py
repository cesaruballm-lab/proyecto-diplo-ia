from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional, List
from datetime import date
from backend.database.supabase_client import supabase

router = APIRouter(
    prefix="/api/v1",
    tags=["API Pública Clientes"]
)

@router.get("/cotizaciones")
def get_cotizaciones(
    fecha: Optional[date] = Query(None, description="Fecha de registro de la cotización (YYYY-MM-DD)"),
    moneda: Optional[str] = Query(None, description="Moneda: 'USD' o 'EUR'"),
    tipo: Optional[str] = Query(None, description="Tipo de cotización: 'billete' o 'divisa'")
):
    """
    Retorna el listado de cotizaciones oficiales.
    Requiere autenticación por cabecera: X-API-Key
    """
    try:
        query = supabase.table("cotizaciones").select("id, fecha_registro, fecha_oficial_bna, hora_actualizacion, moneda, tipo, compra, venta, origen")
        
        # Aplicar filtros si están presentes
        if fecha:
            query = query.eq("fecha_registro", str(fecha))
        if moneda:
            # Normalizar a mayúsculas
            moneda_upper = moneda.upper().strip()
            if moneda_upper not in ["USD", "EUR"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Moneda no válida. Use 'USD' o 'EUR'."
                )
            query = query.eq("moneda", moneda_upper)
        if tipo:
            tipo_lower = tipo.lower().strip()
            if tipo_lower not in ["billete", "divisa"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tipo no válido. Use 'billete' o 'divisa'."
                )
            query = query.eq("tipo", tipo_lower)
            
        # Ordenar por fecha de registro descendente
        query = query.order("fecha_registro", desc=True).order("moneda")
        
        response = query.execute()
        return response.data
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar cotizaciones: {str(e)}"
        )
