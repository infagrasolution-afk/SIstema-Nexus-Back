from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.api.deps import get_db, get_current_tenant
from app.services.dashboard_service import DashboardService

router = APIRouter()

@router.get("/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    period: Optional[str] = Query("month", description="today | week | month | year | all"),
):
    """
    Retorna el resumen ejecutivo del ERP para el dashboard.
    KPIs: ventas, compras, stock, CxC/CxP, low stock, top productos, top clientes.
    """
    return await DashboardService.get_summary(db, tenant_id, period=period)
