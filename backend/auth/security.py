import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Request, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuraciones
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "bna-super-secret-development-key-1234567")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "bna_secure_admin_password_2026")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# --- Gestión de API Keys ---

def generate_new_api_key() -> tuple[str, str, str]:
    """
    Genera una clave API aleatoria y segura.
    Retorna una tupla: (clave_completa, prefijo, hash_sha256)
    """
    # Genera 16 bytes de entropía (32 caracteres hexadecimales)
    token = secrets.token_hex(16)
    full_key = f"bna_live_{token}"
    prefix = f"bna_live_{token[:4]}"
    
    # Hashear clave completa con SHA-256
    hash_object = hashlib.sha256(full_key.encode())
    api_key_hash = hash_object.hexdigest()
    
    return full_key, prefix, api_key_hash

def hash_provided_key(api_key: str) -> str:
    """
    Devuelve el hash SHA-256 de una clave proporcionada.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()

# --- Gestión de Sesiones JWT (Admin) ---

def create_admin_token() -> str:
    """
    Genera un token JWT para la sesión del administrador.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": ADMIN_USERNAME, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_admin_token(token: str) -> bool:
    """
    Verifica si un token JWT es válido.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username == ADMIN_USERNAME:
            return True
    except jwt.PyJWTError:
        return False
    return False

# --- Dependencias de FastAPI ---

def get_current_admin(request: Request) -> str:
    """
    Dependencia para validar que el usuario es un administrador autenticado.
    Busca la cookie 'admin_session'.
    """
    token = request.cookies.get("admin_session")
    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión de administrador no válida o expirada.",
        )
    return ADMIN_USERNAME

async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Dependencia para validar claves API de clientes externos.
    Valida la existencia del header X-API-Key y devuelve la clave.
    El chequeo contra base de datos se realiza en el endpoint o en un middleware de auditoría.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecera X-API-Key ausente.",
        )
    return api_key
