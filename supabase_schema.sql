-- Script para la creación de tablas en Supabase (PostgreSQL)

-- 1. Tabla de Cotizaciones
CREATE TABLE IF NOT EXISTS cotizaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE, -- Fecha del registro en base de datos
    fecha_oficial_bna DATE NOT NULL,                   -- Fecha informada oficialmente por el BNA
    hora_actualizacion VARCHAR(10) NOT NULL,           -- Hora informada oficialmente por el BNA (ej. "17:02")
    moneda VARCHAR(10) NOT NULL CHECK (moneda IN ('USD', 'EUR')),
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('billete', 'divisa')),
    compra NUMERIC(12, 4) NOT NULL,
    venta NUMERIC(12, 4) NOT NULL,
    origen VARCHAR(10) NOT NULL DEFAULT 'scraped' CHECK (origen IN ('scraped', 'manual')),
    creado_por VARCHAR(100) DEFAULT 'sistema',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indice único para asegurar que solo haya un registro de (moneda, tipo) por cada día calendario de registro
CREATE UNIQUE INDEX IF NOT EXISTS idx_cotizaciones_registro_moneda_tipo 
ON cotizaciones (fecha_registro, moneda, tipo);

-- 2. Tabla de API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_nombre VARCHAR(150) NOT NULL,
    cliente_email VARCHAR(150) NOT NULL,
    api_key_hash VARCHAR(64) NOT NULL UNIQUE,          -- Hashed con SHA-256
    api_key_prefix VARCHAR(15) NOT NULL,               -- Prefijo visible en panel de admin
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Tabla de Logs de Auditoría
CREATE TABLE IF NOT EXISTS api_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    endpoint VARCHAR(255) NOT NULL,
    metodo VARCHAR(10) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    status_code INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
