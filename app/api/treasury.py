"""
API de Tesorería — CxC, CxP, Pagos, Aging Report y gestión completa.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.api.deps import get_db, get_current_tenant, get_current_user, require_module
from app.domain.treasury import AccountsReceivable, AccountsPayable, TreasuryPayment, DebtStatus
from app.domain.sales import Customer
from app.domain.purchases import Supplier
from app.schemas.treasury import (
    AccountsReceivableResponse, AccountsPayableResponse,
    AccountsReceivableCreate, AccountsPayableCreate,
    TreasuryPaymentCreate, TreasuryPaymentResponse
)
from app.services.treasury_service import TreasuryService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Cuentas por Cobrar (AR)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ar", response_model=List[AccountsReceivableResponse])
async def get_ar_list(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
    status: Optional[str] = Query(None, description="OPEN | PARTIAL | PAID | OVERDUE"),
    customer_id: Optional[int] = Query(None),
    overdue_only: bool = Query(False, description="Solo CxC vencidas"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Lista Cuentas por Cobrar con filtros opcionales."""
    stmt = (
        select(AccountsReceivable)
        .where(AccountsReceivable.tenant_id == tenant_id)
        .options(selectinload(AccountsReceivable.customer), selectinload(AccountsReceivable.payments))
        .order_by(AccountsReceivable.due_date.asc())
    )
    if status:
        stmt = stmt.where(AccountsReceivable.status == status)
    if customer_id:
        stmt = stmt.where(AccountsReceivable.customer_id == customer_id)
    if overdue_only:
        stmt = stmt.where(
            AccountsReceivable.due_date < datetime.utcnow(),
            AccountsReceivable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/ar", response_model=AccountsReceivableResponse)
async def create_ar_manual(
    ar_in: AccountsReceivableCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
):
    """Crea una CxC manualmente (sin pasar por una venta)."""
    ar = AccountsReceivable(
        sale_id=ar_in.sale_id,
        customer_id=ar_in.customer_id,
        total_amount=ar_in.total_amount,
        remaining_amount=ar_in.total_amount,
        due_date=ar_in.due_date,
        status=DebtStatus.OPEN,
        notes=ar_in.notes,
        tenant_id=tenant_id,
    )
    db.add(ar)
    await db.commit()
    await db.refresh(ar)
    return ar


@router.get("/ar/aging-report")
async def get_ar_aging_report(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
):
    """
    Reporte de Antigüedad de Deudas (Aging Report) de Cuentas por Cobrar.
    Agrupa en: Al día, 1-30 días vencido, 31-60, 61-90, +90 días.
    """
    now = datetime.utcnow()
    result = await db.execute(
        select(AccountsReceivable)
        .where(
            AccountsReceivable.tenant_id == tenant_id,
            AccountsReceivable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
        .options(selectinload(AccountsReceivable.customer))
    )
    ar_list = result.scalars().all()

    buckets = {"current": [], "1_30": [], "31_60": [], "61_90": [], "over_90": []}
    totals = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}

    for ar in ar_list:
        days_overdue = (now - ar.due_date).days if ar.due_date < now else 0
        record = {
            "id": ar.id,
            "customer": ar.customer.name if ar.customer else "N/A",
            "total": ar.total_amount,
            "remaining": ar.remaining_amount,
            "due_date": ar.due_date.isoformat(),
            "days_overdue": max(0, days_overdue),
        }
        if days_overdue <= 0:
            bucket = "current"
        elif days_overdue <= 30:
            bucket = "1_30"
        elif days_overdue <= 60:
            bucket = "31_60"
        elif days_overdue <= 90:
            bucket = "61_90"
        else:
            bucket = "over_90"
        buckets[bucket].append(record)
        totals[bucket] += ar.remaining_amount

    return {
        "generated_at": now.isoformat(),
        "buckets": buckets,
        "totals": totals,
        "grand_total": sum(totals.values()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Cuentas por Pagar (AP)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ap", response_model=List[AccountsPayableResponse])
async def get_ap_list(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
    status: Optional[str] = Query(None, description="OPEN | PARTIAL | PAID | OVERDUE"),
    supplier_id: Optional[int] = Query(None),
    overdue_only: bool = Query(False, description="Solo CxP vencidas"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Lista Cuentas por Pagar con filtros opcionales."""
    stmt = (
        select(AccountsPayable)
        .where(AccountsPayable.tenant_id == tenant_id)
        .options(selectinload(AccountsPayable.supplier), selectinload(AccountsPayable.payments))
        .order_by(AccountsPayable.due_date.asc())
    )
    if status:
        stmt = stmt.where(AccountsPayable.status == status)
    if supplier_id:
        stmt = stmt.where(AccountsPayable.supplier_id == supplier_id)
    if overdue_only:
        stmt = stmt.where(
            AccountsPayable.due_date < datetime.utcnow(),
            AccountsPayable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/ap", response_model=AccountsPayableResponse)
async def create_ap_manual(
    ap_in: AccountsPayableCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
):
    """Crea una CxP manualmente (sin pasar por una compra)."""
    ap = AccountsPayable(
        purchase_id=ap_in.purchase_id,
        supplier_id=ap_in.supplier_id,
        total_amount=ap_in.total_amount,
        remaining_amount=ap_in.total_amount,
        due_date=ap_in.due_date,
        status=DebtStatus.OPEN,
        notes=ap_in.notes,
        tenant_id=tenant_id,
    )
    db.add(ap)
    await db.commit()
    await db.refresh(ap)
    return ap


@router.get("/ap/aging-report")
async def get_ap_aging_report(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
):
    """Reporte de Antigüedad de CxP (Aging Report)."""
    now = datetime.utcnow()
    result = await db.execute(
        select(AccountsPayable)
        .where(
            AccountsPayable.tenant_id == tenant_id,
            AccountsPayable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
        .options(selectinload(AccountsPayable.supplier))
    )
    ap_list = result.scalars().all()

    buckets = {"current": [], "1_30": [], "31_60": [], "61_90": [], "over_90": []}
    totals = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}

    for ap in ap_list:
        days_overdue = (now - ap.due_date).days if ap.due_date < now else 0
        record = {
            "id": ap.id,
            "supplier": ap.supplier.name if ap.supplier else "N/A",
            "total": ap.total_amount,
            "remaining": ap.remaining_amount,
            "due_date": ap.due_date.isoformat(),
            "days_overdue": max(0, days_overdue),
        }
        if days_overdue <= 0:
            bucket = "current"
        elif days_overdue <= 30:
            bucket = "1_30"
        elif days_overdue <= 60:
            bucket = "31_60"
        elif days_overdue <= 90:
            bucket = "61_90"
        else:
            bucket = "over_90"
        buckets[bucket].append(record)
        totals[bucket] += ap.remaining_amount

    return {
        "generated_at": now.isoformat(),
        "buckets": buckets,
        "totals": totals,
        "grand_total": sum(totals.values()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pagos
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/payments", response_model=TreasuryPaymentResponse)
async def create_payment(
    payment_in: TreasuryPaymentCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_module("treasury")),
):
    """Registra un pago (cobro AR o pago AP). Actualiza el saldo automáticamente."""
    return await TreasuryService.process_payment(
        db, payment_in, tenant_id,
        user_id=current_user.id, user_name=current_user.username
    )


@router.get("/payments", response_model=List[TreasuryPaymentResponse])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
    ar_id: Optional[int] = Query(None),
    ap_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Lista pagos con filtros opcionales."""
    stmt = (
        select(TreasuryPayment)
        .where(TreasuryPayment.tenant_id == tenant_id)
        .order_by(TreasuryPayment.payment_date.desc())
    )
    if ar_id:
        stmt = stmt.where(TreasuryPayment.ar_id == ar_id)
    if ap_id:
        stmt = stmt.where(TreasuryPayment.ap_id == ap_id)
    if date_from:
        stmt = stmt.where(TreasuryPayment.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(TreasuryPayment.payment_date <= date_to)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/summary")
async def get_treasury_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("treasury")),
):
    """Resumen ejecutivo de tesorería: totales AR/AP abiertos, vencidos y cobrados."""
    now = datetime.utcnow()

    ar_total_open = await db.scalar(
        select(func.sum(AccountsReceivable.remaining_amount)).where(
            AccountsReceivable.tenant_id == tenant_id,
            AccountsReceivable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
    )
    ar_total_paid = await db.scalar(
        select(func.sum(AccountsReceivable.total_amount)).where(
            AccountsReceivable.tenant_id == tenant_id,
            AccountsReceivable.status == DebtStatus.PAID
        )
    )
    ar_overdue = await db.scalar(
        select(func.sum(AccountsReceivable.remaining_amount)).where(
            AccountsReceivable.tenant_id == tenant_id,
            AccountsReceivable.due_date < now,
            AccountsReceivable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
    )

    ap_total_open = await db.scalar(
        select(func.sum(AccountsPayable.remaining_amount)).where(
            AccountsPayable.tenant_id == tenant_id,
            AccountsPayable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
    )
    ap_total_paid = await db.scalar(
        select(func.sum(AccountsPayable.total_amount)).where(
            AccountsPayable.tenant_id == tenant_id,
            AccountsPayable.status == DebtStatus.PAID
        )
    )
    ap_overdue = await db.scalar(
        select(func.sum(AccountsPayable.remaining_amount)).where(
            AccountsPayable.tenant_id == tenant_id,
            AccountsPayable.due_date < now,
            AccountsPayable.status.in_([DebtStatus.OPEN, DebtStatus.PARTIAL])
        )
    )

    return {
        "accounts_receivable": {
            "open": float(ar_total_open or 0),
            "paid": float(ar_total_paid or 0),
            "overdue": float(ar_overdue or 0),
        },
        "accounts_payable": {
            "open": float(ap_total_open or 0),
            "paid": float(ap_total_paid or 0),
            "overdue": float(ap_overdue or 0),
        },
        "net_position": float((ar_total_open or 0) - (ap_total_open or 0)),
        "generated_at": now.isoformat(),
    }
