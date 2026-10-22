"""
API de Caja — Gestión completa de sesiones de caja, arqueo y reportes de cierre.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.api import deps
from app.api.deps import require_module
from app.services.cash_service import CashService
from app.schemas.cash import CashSession, CashSessionCreate, CashSessionClose, CashRegister
from app.domain.user import User
from app.domain.cash import CashSession as DBCashSession, CashRegister as DBCashRegister
from app.domain.sales import Sale

router = APIRouter()


@router.get("/session/current", response_model=Optional[CashSession])
async def get_current_session(
    computer_uid: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Obtiene la sesión de caja actualmente abierta para este equipo."""
    return await CashService.get_current_session(db, computer_uid, current_user.tenant_id)


@router.post("/session/open", response_model=CashSession)
async def open_session(
    session_in: CashSessionCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Abre una sesión de caja para el equipo especificado.
    Si ya hay una sesión abierta por otro usuario, rechaza la apertura.
    """
    return await CashService.open_session(db, session_in, current_user.id, current_user.tenant_id)


@router.post("/session/{session_id}/close", response_model=CashSession)
async def close_session(
    session_id: int,
    close_in: CashSessionClose,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Cierra una sesión de caja. Calcula el efectivo esperado vs. reportado.
    La diferencia (sobrante/faltante) queda registrada.
    """
    return await CashService.close_session(db, session_id, close_in, current_user.tenant_id)


@router.get("/session/{session_id}/report")
async def get_session_report(
    session_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Reporte de cierre de sesión de caja.
    Desglose por método de pago, ventas por hora, diferencia de arqueo.
    """
    tenant_id = current_user.tenant_id

    # Load session
    session_result = await db.execute(
        select(DBCashSession)
        .where(DBCashSession.id == session_id, DBCashSession.tenant_id == tenant_id)
        .options(selectinload(DBCashSession.register))
    )
    session = session_result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión de caja no encontrada")

    # Get all sales for this session
    sales_result = await db.execute(
        select(Sale).where(
            Sale.cash_session_id == session_id,
            Sale.tenant_id == tenant_id,
            Sale.status == "COMPLETED"
        )
    )
    sales = sales_result.scalars().all()

    # Breakdown by payment method
    payment_breakdown = {}
    for sale in sales:
        method = sale.payment_method or "cash"
        if method not in payment_breakdown:
            payment_breakdown[method] = {"count": 0, "total": 0.0}
        payment_breakdown[method]["count"] += 1
        payment_breakdown[method]["total"] += sale.total

    total_sales_amount = sum(s.total for s in sales)
    total_sales_count = len(sales)
    cash_sales = payment_breakdown.get("cash", {}).get("total", 0.0)

    expected = (session.starting_cash or 0) + cash_sales
    actual = session.actual_cash or 0
    difference = actual - expected

    return {
        "session_id": session_id,
        "register_name": session.register.name if session.register else "N/A",
        "opening_time": session.opening_time.isoformat() if session.opening_time else None,
        "closing_time": session.closing_time.isoformat() if session.closing_time else None,
        "status": session.status,
        # Fondos
        "starting_cash": session.starting_cash or 0,
        "expected_cash": expected,
        "actual_cash": actual,
        "difference": round(difference, 2),
        "difference_label": "Sobrante" if difference > 0 else "Faltante" if difference < 0 else "Cuadrado",
        # Ventas
        "total_sales_count": total_sales_count,
        "total_sales_amount": round(total_sales_amount, 2),
        "payment_breakdown": payment_breakdown,
    }


@router.get("/sessions", response_model=List[CashSession])
async def list_sessions(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    status: Optional[str] = Query(None, description="open | closed"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """Lista historial de sesiones de caja para el tenant."""
    stmt = (
        select(DBCashSession)
        .where(DBCashSession.tenant_id == current_user.tenant_id)
        .options(selectinload(DBCashSession.register))
        .order_by(DBCashSession.opening_time.desc())
    )
    if status:
        stmt = stmt.where(DBCashSession.status == status)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    # Eagerly assign register to prevent lazyload errors
    return sessions


@router.get("/registers", response_model=List[CashRegister])
async def get_registers(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Lista todas las cajas registradoras del tenant."""
    stmt = select(DBCashRegister).where(DBCashRegister.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()
