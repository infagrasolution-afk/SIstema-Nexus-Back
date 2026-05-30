from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import inventory, sales, auth, dashboard, suppliers, purchases, users, tenants, admin, cash, accounting, treasury, roles, movements, manual

app = FastAPI(
    title="ERP Multi-Tenant API",
    description="API for the multi-tenant ERP system focused on Inventory and Sales.",
    version="1.0.0",
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        from app.scripts.update_db import update_all_databases
        await update_all_databases()
        print("Database schema sync completed successfully on startup!")
    except Exception as e:
        print(f"Error during startup database update: {e}")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)},
    )

@app.get("/")
async def root():
    return {"message": "Welcome to the ERP Multi-Tenant API"}

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
