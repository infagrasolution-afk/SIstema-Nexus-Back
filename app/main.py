import os
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.core.database import dispose_all_engines, master_engine
from app.api import (
    inventory, sales, auth, dashboard, suppliers, purchases,
    users, tenants, admin, cash, accounting, treasury, roles,
    movements, manual, support, fiscal, payroll
)

# Configuración de registro de eventos (logging)
logging.basicConfig(
    level=logging.INFO if settings.is_production else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("apex.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: sincronizar esquemas de base de datos
    try:
        from app.scripts.update_db import update_all_databases
        await update_all_databases()
        logger.info("Sincronización de esquemas completada exitosamente al iniciar.")
    except Exception as e:
        logger.error(f"Error durante la sincronización inicial de base de datos: {e}")
    yield
    # Shutdown: liberar conexiones de engines
    try:
        await dispose_all_engines()
        logger.info("Conexiones de base de datos liberadas correctamente al apagar el servidor.")
    except Exception as e:
        logger.error(f"Error al cerrar conexiones de base de datos: {e}")


app = FastAPI(
    title="APEX ERP API",
    description="Ecosistema ERP Empresarial Multi-Tenant Adaptado a Venezuela (SENIAT / LOTTT).",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS or not settings.is_production else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS or not settings.is_production else None,
)

# ── Configuración de CORS Segura ──────────────────────────────────────────────
# Se restringe a la lista autorizada en ALLOWED_ORIGINS más subdominios propios de Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://[a-zA-Z0-9-]+\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Total-Count"],
)


# ── Cabeceras Profesionales de Seguridad (HSTS, CSP, etc.) ────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Control de tamaño máximo de petición para evitar ataques de denegación de servicio (DoS)
    content_length = request.headers.get("content-length")
    max_bytes = settings.MAX_REQUEST_BODY_MB * 1024 * 1024
    if content_length and int(content_length) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": f"El archivo o contenido enviado supera el límite permitido ({settings.MAX_REQUEST_BODY_MB} MB)."}
        )

    response = await call_next(request)

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response


# Directorio estático seguro para descargas y recursos
os.makedirs("static/downloads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Manejador Global de Excepciones Seguro (Sin fuga de datos internos) ───────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    ref_id = f"APEX-{uuid.uuid4().hex[:8].upper()}"
    error_str = str(exc)
    logger.error(f"[{ref_id}] Error no controlado en {request.method} {request.url.path}: {exc}", exc_info=True)

    origin = request.headers.get("origin") or "*"
    headers = {
        "Access-Control-Allow-Origin": origin if origin != "*" else "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }

    if "connection was closed" in error_str.lower() or "connectiondoesnotexist" in error_str.lower():
        user_message = (
            "No se pudo establecer conexión temporal con la base de datos central. "
            "Por favor, intenta nuevamente en unos instantes."
        )
    else:
        user_message = (
            f"Ocurrió un problema técnico inesperado al procesar la solicitud. "
            f"Si persiste, comunica este código de referencia a soporte técnico: {ref_id}"
        )

    content = {
        "detail": user_message,
        "reference_id": ref_id,
    }
    # En entorno de desarrollo incluimos detalles técnicos para agilizar la depuración
    if not settings.is_production:
        content["debug_message"] = error_str

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
        headers=headers,
    )


# ── Endpoints Base y Verificación de Salud (Health Check) ─────────────────────
@app.get("/")
async def root():
    return {
        "system": "APEX ERP",
        "version": settings.VERSION,
        "status": "online",
        "edition": "Venezuela Multi-Tenant (SENIAT / LOTTT)"
    }


@app.get("/health")
async def health_check():
    """Endpoint de monitoreo utilizado por Render para verificar la salud del backend."""
    db_healthy = False
    try:
        async with master_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_healthy = True
    except Exception as e:
        logger.warning(f"Health check DB probe warning: {e}")

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "unavailable",
        "version": settings.VERSION
    }


# ── Registro de Módulos y Enrutadores de la API ──────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación y Sesiones"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Panel de Control (Dashboard)"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventario y Almacenes (WMS)"])
app.include_router(sales.router, prefix="/api/v1/sales", tags=["Ventas y Facturación"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["Proveedores"])
app.include_router(purchases.router, prefix="/api/v1/purchases", tags=["Compras"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Usuarios y Accesos"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Empresas y Sucursales"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Súper Administrador SaaS"])
app.include_router(cash.router, prefix="/api/v1/cash", tags=["Gestión de Caja y Arqueo"])
app.include_router(accounting.router, prefix="/api/v1/accounting", tags=["Contabilidad VEN-NIF"])
app.include_router(treasury.router, prefix="/api/v1/treasury", tags=["Tesorería (CxC / CxP)"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles y Permisos"])
app.include_router(movements.router, prefix="/api/v1/movements", tags=["Auditoría de Movimientos"])
app.include_router(manual.router, prefix="/api/v1/manual", tags=["Manual de Usuario"])
app.include_router(support.router, prefix="/api/v1/support", tags=["Soporte e Incidencias"])
app.include_router(fiscal.router, prefix="/api/v1/fiscal", tags=["Fiscal (SENIAT Venezuela)"])
app.include_router(payroll.router, prefix="/api/v1/payroll", tags=["Nómina y RRHH (LOTTT)"])
