"""
API de Compras — Módulo completo con flujo DRAFT → APPROVED → RECEIVED.
Incluye filtros, búsqueda, cancelación y actualización de órdenes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.api.deps import get_db, get_current_tenant, get_current_user, require_module
from app.services.purchase_service import PurchaseService
from app.schemas.purchases import (
    PurchaseCreate, PurchaseResponse, PurchaseUpdate,
    PurchaseReceiveIn
)
from app.domain.purchases import Purchase, PurchaseStatus, Supplier

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# CRUD Base
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=PurchaseResponse)
async def create_purchase(
    purchase_in: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_module("purchases")),
):
    """Crea una nueva orden de compra. El estado inicial depende del campo 'draft': si es True, queda en DRAFT; si es False, se completa directamente."""
    try:
        return await PurchaseService.create_purchase(
            db, purchase_in, tenant_id,
            user_id=current_user.id, user_name=current_user.username
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[PurchaseResponse])
async def get_purchases(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("purchases")),
    status: Optional[str] = Query(None, description="DRAFT | APPROVED | COMPLETED | CANCELLED"),
    supplier_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None, description="Buscar por referencia"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Lista órdenes de compra con filtros opcionales."""
    stmt = (
        select(Purchase)
        .where(Purchase.tenant_id == tenant_id)
        .options(
            selectinload(Purchase.details),
            selectinload(Purchase.supplier),
        )
        .order_by(Purchase.created_at.desc())
    )
    if status:
        stmt = stmt.where(Purchase.status == status)
    if supplier_id:
        stmt = stmt.where(Purchase.supplier_id == supplier_id)
    if date_from:
        stmt = stmt.where(Purchase.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Purchase.created_at <= date_to)
    if search:
        stmt = stmt.where(Purchase.reference.ilike(f"%{search}%"))
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{purchase_id}", response_model=PurchaseResponse)
async def get_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("purchases")),
):
    """Obtiene el detalle de una orden de compra específica."""
    result = await db.execute(
        select(Purchase)
        .where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
        .options(selectinload(Purchase.details), selectinload(Purchase.supplier))
    )
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    return purchase


@router.put("/{purchase_id}", response_model=PurchaseResponse)
async def update_purchase(
    purchase_id: int,
    purchase_in: PurchaseUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("purchases")),
):
    """Actualiza la referencia o el método de pago de una OC en estado DRAFT."""
    result = await db.execute(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
    )
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    if purchase.status not in [PurchaseStatus.DRAFT]:
        raise HTTPException(status_code=400, detail="Solo se pueden editar OC en estado DRAFT")

    for field, value in purchase_in.model_dump(exclude_unset=True).items():
        setattr(purchase, field, value)

    await db.commit()
    await db.refresh(purchase)
    return purchase


# ─────────────────────────────────────────────────────────────────────────────
# Flujo de Estados
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/{purchase_id}/approve")
async def approve_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_module("purchases")),
):
    """Aprueba una OC en estado DRAFT → APPROVED. No mueve inventario todavía."""
    result = await db.execute(
        select(Purchase).where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
    )
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="OC no encontrada")
    if purchase.status != PurchaseStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"La OC ya tiene estado '{purchase.status}', solo se pueden aprobar OC en DRAFT")

    purchase.status = PurchaseStatus.APPROVED
    await db.commit()
    return {"status": "success", "message": f"OC #{purchase_id} aprobada. Puede proceder a la recepción de mercancía."}


@router.post("/{purchase_id}/receive")
async def receive_purchase(
    purchase_id: int,
    receive_in: PurchaseReceiveIn,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_module("purchases")),
):
    """
    Recibe mercancía de una OC aprobada → COMPLETED.
    Carga el inventario, actualiza costo promedio y genera CxP si aplica.
    Soporta recepción parcial.
    """
    result = await db.execute(
        select(Purchase)
        .where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
        .options(selectinload(Purchase.details))
    )
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="OC no encontrada")
    if purchase.status not in [PurchaseStatus.APPROVED, PurchaseStatus.DRAFT]:
        raise HTTPException(status_code=400, detail=f"La OC tiene estado '{purchase.status}'. Solo se pueden recibir OC APPROVED o DRAFT.")

    try:
        return await PurchaseService.receive_purchase(
            db=db,
            purchase=purchase,
            receive_in=receive_in,
            tenant_id=tenant_id,
            user_id=current_user.id,
            user_name=current_user.username,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{purchase_id}/cancel")
async def cancel_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user=Depends(get_current_user),
    _: bool = Depends(require_module("purchases")),
):
    """Cancela una OC. Si ya fue COMPLETED, genera reversa de inventario."""
    result = await db.execute(
        select(Purchase)
        .where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
        .options(selectinload(Purchase.details))
    )
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="OC no encontrada")
    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="La OC ya está cancelada")

    prev_status = purchase.status
    purchase.status = PurchaseStatus.CANCELLED

    # Si estaba completada, revertir inventario
    if prev_status == PurchaseStatus.COMPLETED:
        from app.services.wms_service import WMSService
        from app.domain.inventory import MovementType, MovementSubtype
        for detail in purchase.details:
            try:
                await WMSService.register_movement(
                    db=db,
                    product_id=detail.product_id,
                    warehouse_id=receive_in.warehouse_id if hasattr(receive_in, 'warehouse_id') else 1,
                    movement_type=MovementType.OUT,
                    movement_subtype=MovementSubtype.ADJUSTMENT,
                    quantity=detail.quantity,
                    reference=f"Reversa Compra Cancelada #{purchase.id:06d}",
                    tenant_id=tenant_id,
                    user_id=current_user.id,
                    user_name=current_user.username,
                )
            except Exception:
                pass

    await db.commit()
    return {
        "status": "success",
        "message": f"OC #{purchase_id} cancelada",
        "reverted_inventory": prev_status == PurchaseStatus.COMPLETED
    }
