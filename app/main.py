from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from app.core.config import settings
from app.core.database import dispose_all_engines
from app.api import (
    inventory, sales, auth, dashboard, suppliers, purchases,
    users, tenants, admin, cash, accounting, treasury, roles,
    movements, manual, support, fiscal, payroll
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: sincronizar esquemas de base de datos
    try:
        from app.scripts.update_db import update_all_databases
        await update_all_databases()
        print("Database schema sync completed successfully on startup!")
    except Exception as e:
        print(f"Error during startup database update: {e}")
    yield
    # Shutdown: liberar conexiones de engines
    try:
        await dispose_all_engines()
        print("Database engines disposed successfully on shutdown.")
    except Exception as e:
        print(f"Error during shutdown: {e}")

app = FastAPI(
    title="Nexus ERP API",
    description="API for the multi-tenant Nexus ERP system with Venezuelan SENIAT compliance.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Professional Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    return response

# Create static directory if not exists
os.makedirs("static/downloads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)},
    )

@app.get("/")
async def root():
    return {"message": "Welcome to the Nexus ERP Multi-Tenant API (Venezuela Edition)"}

# API Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(sales.router, prefix="/api/v1/sales", tags=["Sales"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["Suppliers"])
app.include_router(purchases.router, prefix="/api/v1/purchases", tags=["Purchases"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenants"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["SuperAdmin"])
app.include_router(cash.router, prefix="/api/v1/cash", tags=["Cash Management"])
app.include_router(accounting.router, prefix="/api/v1/accounting", tags=["Accounting"])
app.include_router(treasury.router, prefix="/api/v1/treasury", tags=["Treasury"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles & Permissions"])
app.include_router(movements.router, prefix="/api/v1/movements", tags=["System Movements"])
app.include_router(manual.router, prefix="/api/v1/manual", tags=["User Manual"])
app.include_router(support.router, prefix="/api/v1/support", tags=["Support & Error Logs"])
app.include_router(fiscal.router, prefix="/api/v1/fiscal", tags=["Fiscal (SENIAT Venezuela)"])
app.include_router(payroll.router, prefix="/api/v1/payroll", tags=["Nómina y RRHH (LOTTT Venezuela)"])
