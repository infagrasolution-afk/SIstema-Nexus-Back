"""
API de Movimientos del Sistema — Historial universal de todas las operaciones del ERP.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_db, get_current_tenant, get_current_user
from app.domain.system_movement import SystemMovement
from app.domain.user import User

router = APIRouter()


class SystemMovementResponse(BaseModel):
    id: int
    tenant_id: int
    created_at: datetime
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    module: str
    operation: str
    reference_id: Optional[int] = None
    reference_type: Optional[str] = None
    reference_code: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    warehouse_id: Optional[int] = None
    warehouse_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    amount: Optional[float] = None
    unit_cost: Optional[float] = None
    currency: Optional[str] = None
    description: str
    notes: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SystemMovementResponse])
async def get_system_movements(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    # Filtros opcionales
    module: Optional[str] = Query(None, description="INVENTORY | SALES | PURCHASES | TREASURY | ACCOUNTING | CASH"),
    operation: Optional[str] = Query(None, description="CHARGE | DISCHARGE | SALE | PURCHASE | PAYMENT_AR | ..."),
    product_id: Optional[int] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """
    Retorna el historial universal de movimientos del sistema.
    Filtra por módulo, operación, producto, almacén, usuario y rango de fechas.
    """
    filters = [SystemMovement.tenant_id == tenant_id]

    if module:
        filters.append(SystemMovement.module == module.upper())
    if operation:
        filters.append(SystemMovement.operation == operation.upper())
    if product_id:
        filters.append(SystemMovement.product_id == product_id)
    if warehouse_id:
        filters.append(SystemMovement.warehouse_id == warehouse_id)
    if user_id:
        filters.append(SystemMovement.user_id == user_id)
    if date_from:
        filters.append(SystemMovement.created_at >= date_from)
    if date_to:
        filters.append(SystemMovement.created_at <= date_to)

    stmt = (
        select(SystemMovement)
        .where(and_(*filters))
        .order_by(SystemMovement.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/summary")
async def get_movements_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """
    Retorna un resumen de movimientos agrupado por módulo y operación.
    """
    from sqlalchemy import func
    filters = [SystemMovement.tenant_id == tenant_id]
    if date_from:
        filters.append(SystemMovement.created_at >= date_from)
    if date_to:
        filters.append(SystemMovement.created_at <= date_to)

    stmt = (
        select(
            SystemMovement.module,
            SystemMovement.operation,
            func.count(SystemMovement.id).label("total"),
            func.sum(SystemMovement.amount).label("total_amount"),
            func.sum(SystemMovement.quantity).label("total_quantity"),
        )
        .where(and_(*filters))
        .group_by(SystemMovement.module, SystemMovement.operation)
        .order_by(SystemMovement.module, SystemMovement.operation)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "module": r.module,
            "operation": r.operation,
            "total": r.total,
            "total_amount": round(r.total_amount or 0, 2),
            "total_quantity": round(r.total_quantity or 0, 4),
        }
        for r in rows
    ]
