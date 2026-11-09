from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, or_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.api.deps import get_db, get_current_tenant, get_current_user, require_module, require_permissions
from app.services.sales_service import SalesService
from app.services.pdf_service import PDFService
from app.schemas.sales import (
    SaleCreate, SaleResponse, BudgetCreate, BudgetResponse,
    CustomerCreate, CustomerResponse, CustomerUpdate,
    DebitNoteCreate, DebitNoteResponse,
    CreditNoteCreate, CreditNoteResponse
)
from app.domain.sales import Sale, Budget, Customer, CreditNote, CreditNoteItem
from app.domain.accounting import DebitNote
from app.domain.tenant import Tenant
from app.domain.user import User

router = APIRouter()

@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales")),
    _perm: User = Depends(require_permissions(["sales:write"])),
):
    try:
        return await SalesService.create_sale(db, sale_in, tenant_id, current_user.id, current_user.username)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=list[SaleResponse])
async def list_sales(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales")),
    _perm: User = Depends(require_permissions(["sales:read"])),
    status: Optional[str] = Query(None, description="COMPLETED | ON_HOLD | CANCELLED"),
    customer_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None, description="Buscar por número de factura o nota"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """Lista ventas con filtros opcionales por estado, cliente, fecha y búsqueda."""
    stmt = (
        select(Sale)
        .where(Sale.tenant_id == tenant_id)
        .options(selectinload(Sale.details), selectinload(Sale.customer))
        .order_by(Sale.created_at.desc())
    )
    if status:
        stmt = stmt.where(Sale.status == status)
    if customer_id:
        stmt = stmt.where(Sale.customer_id == customer_id)
    if date_from:
        stmt = stmt.where(Sale.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Sale.created_at <= date_to)
    if search:
        stmt = stmt.where(
            or_(
                Sale.fiscal_invoice_number.ilike(f"%{search}%"),
                Sale.printer_serial.ilike(f"%{search}%"),
            )
        )
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/customers/fiscal", response_model=dict)
async def find_or_create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales")),
):
    try:
        customer = await SalesService.find_or_create_customer(db, customer_in, tenant_id, current_user.id, current_user.username)
        return {"id": customer.id, "name": customer.name, "tax_id": customer.tax_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/on-hold", response_model=list[SaleResponse])
async def get_on_hold_sales(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales")),
):
    result = await db.execute(
        select(Sale)
        .where(Sale.status == "ON_HOLD", Sale.tenant_id == tenant_id)
        .options(selectinload(Sale.details), selectinload(Sale.customer))
        .order_by(Sale.created_at.desc())
    )
    return result.scalars().all()

@router.put("/{sale_id}/complete")
async def complete_on_hold_sale(
    sale_id: int,
    warehouse_id: int = Query(..., description="ID del almacén del cual descontar el stock"),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """Completa una venta en espera (ON_HOLD): descuenta inventario, registra CxC y bitácora."""
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.tenant_id == tenant_id, Sale.status == "ON_HOLD")
        .options(selectinload(Sale.details), selectinload(Sale.customer))
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada o no está en espera")

    sale.status = "COMPLETED"

    from app.services.wms_service import WMSService
    from app.domain.inventory import MovementType, MovementSubtype
    from app.services.treasury_service import TreasuryService
    from app.services.movement_logger import MovementLogger

    # Descontar inventario por cada línea de la venta
    for detail in sale.details:
        await WMSService.register_movement(
            db=db,
            product_id=detail.product_id,
            warehouse_id=warehouse_id,
            movement_type=MovementType.OUT,
            movement_subtype=MovementSubtype.SALE,
            quantity=detail.quantity,
            reference=f"Completar Venta #{sale.id:06d} (era ON_HOLD)",
            tenant_id=tenant_id,
            user_id=current_user.id,
            user_name=current_user.username,
        )

    # Crear CxC si fue a crédito
    if sale.payment_method == "credit":
        await TreasuryService.create_ar(db, sale.id, sale.customer_id, sale.total, tenant_id)

    # Registrar en bitácora
    customer_name = sale.customer.name if sale.customer else f"Cliente #{sale.customer_id}"
    await MovementLogger.log_sale(
        db=db,
        tenant_id=tenant_id,
        sale_id=sale.id,
        customer_name=customer_name,
        total=sale.total,
        currency=sale.currency or "VES",
        payment_method=sale.payment_method,
        user_id=current_user.id,
        user_name=current_user.username,
        status="COMPLETED",
    )

    await db.commit()
    return {"status": "success", "message": f"Venta #{sale_id} completada exitosamente"}


@router.put("/{sale_id}/cancel")
async def cancel_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales")),
    _perm: User = Depends(require_permissions(["sales:void"])),
):
    """Cancela una venta. Si estaba COMPLETED, revierte el inventario. No cancela ventas de caja cerrada."""
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        .options(selectinload(Sale.details))
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if sale.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="La venta ya está cancelada")

    prev_status = sale.status
    sale.status = "CANCELLED"

    # Si estaba completada, revertir inventario en el almacén de origen de la venta
    if prev_status == "COMPLETED":
        from app.services.wms_service import WMSService
        from app.domain.inventory import MovementType, MovementSubtype
        target_warehouse_id = sale.warehouse_id or 1
        for detail in sale.details:
            try:
                await WMSService.register_movement(
                    db=db,
                    product_id=detail.product_id,
                    warehouse_id=target_warehouse_id,
                    movement_type=MovementType.IN,
                    movement_subtype=MovementSubtype.ADJUSTMENT,
                    quantity=detail.quantity,
                    reference=f"Reversa Venta Cancelada #{sale.id:06d}",
                    tenant_id=tenant_id,
                    user_id=current_user.id,
                    user_name=current_user.username,
                )
            except Exception as e:
                import logging
                logging.getLogger("nexus.sales").error(
                    f"Error revirtiendo inventario para producto {detail.product_id} en venta #{sale.id}: {e}"
                )

    await db.commit()
    return {"status": "success", "message": f"Venta #{sale_id} cancelada", "reverted_inventory": prev_status == "COMPLETED"}

@router.get("/{sale_id}/invoice")
async def get_sale_invoice(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        .options(selectinload(Sale.details), selectinload(Sale.customer), selectinload(Sale.tenant))
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    pdf_buffer = PDFService.generate_invoice(sale)
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{sale_id}.pdf"}
    )

@router.get("/{sale_id}/ticket")
async def get_sale_ticket(
    sale_id: int,
    width: int = 80,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    """Genera el Ticket Térmico de Venta para impresoras POS de 80mm o 58mm."""
    result = await db.execute(
        select(Sale)
        .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        .options(selectinload(Sale.details), selectinload(Sale.customer), selectinload(Sale.tenant))
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    pdf_buffer = PDFService.generate_thermal_ticket(sale, width_mm=width)
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=ticket_{sale_id}.pdf"}
    )

@router.get("/budgets", response_model=list[BudgetResponse])
async def get_budgets(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Budget)
        .where(Budget.tenant_id == tenant_id)
        .order_by(Budget.created_at.desc())
    )
    return result.scalars().all()

@router.post("/budgets", response_model=BudgetResponse)
async def create_budget(
    budget_in: BudgetCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    try:
        return await SalesService.create_budget(db, budget_in, tenant_id, current_user.id, current_user.username)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/budgets/{budget_id}/approve")
async def approve_budget(
    budget_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(Budget).where(Budget.id == budget_id, Budget.tenant_id == tenant_id)
    )
    budget = result.scalars().first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    budget.status = "APPROVED"
    await db.commit()
    return {"status": "success", "message": "Budget approved"}


# --- Customer CRUD & Bulk Import ---
@router.get("/customers", response_model=List[CustomerResponse])
async def get_all_customers(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales"))
):
    result = await db.execute(
        select(Customer)
        .where(Customer.tenant_id == tenant_id)
        .order_by(Customer.name.asc())
    )
    return result.scalars().all()


@router.post("/customers", response_model=CustomerResponse)
async def create_new_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales"))
):
    # Check if duplicate tax_id exists
    dup_check = await db.execute(
        select(Customer).where(Customer.tax_id == customer_in.tax_id, Customer.tenant_id == tenant_id)
    )
    if dup_check.scalars().first():
        raise HTTPException(status_code=400, detail="El RIF / Cédula ya está registrado.")

    new_cust = Customer(
        **customer_in.model_dump(),
        tenant_id=tenant_id,
        created_by_id=current_user.id,
        created_by_name=current_user.username
    )
    db.add(new_cust)
    await db.commit()
    await db.refresh(new_cust)
    return new_cust


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer_endpoint(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales"))
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    for field, value in customer_in.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer_endpoint(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales"))
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    await db.delete(customer)
    await db.commit()
    return {"message": "Cliente eliminado"}


@router.post("/customers/import")
async def import_customers_bulk(
    customers_in: List[CustomerCreate],
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales"))
):
    imported_count = 0
    errors = []
    
    for idx, c_in in enumerate(customers_in):
        if not c_in.tax_id or not c_in.name:
            errors.append(f"Fila {idx+1}: Nombre y RIF/Cédula son obligatorios.")
            continue
            
        # Check if already exists
        check_stmt = select(Customer).where(Customer.tax_id == c_in.tax_id, Customer.tenant_id == tenant_id)
        res = await db.execute(check_stmt)
        existing = res.scalars().first()
        
        if existing:
            # Update existing info
            existing.name = c_in.name
            if c_in.phone is not None: existing.phone = c_in.phone
            if c_in.email is not None: existing.email = c_in.email
            if c_in.address is not None: existing.address = c_in.address
        else:
            # Create new
            new_c = Customer(
                **c_in.model_dump(),
                tenant_id=tenant_id,
                created_by_id=current_user.id,
                created_by_name=current_user.username
            )
            db.add(new_c)
        imported_count += 1
        
    await db.commit()
    return {"status": "success", "imported": imported_count, "errors": errors}

# --- Debit/Credit Notes ---
from app.domain.treasury import AccountsReceivable

@router.get("/commercial-notes", response_model=List[DebitNoteResponse])
async def get_commercial_notes(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales"))
):
    result = await db.execute(
        select(DebitNote)
        .join(Customer, DebitNote.customer_id == Customer.id)
        .where(Customer.tenant_id == tenant_id)
        .order_by(DebitNote.created_at.desc())
    )
    return result.scalars().all()

@router.post("/commercial-notes", response_model=DebitNoteResponse)
async def create_commercial_note(
    note_in: DebitNoteCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales"))
):
    # Ensure customer belongs to tenant
    cust_check = await db.execute(
        select(Customer).where(Customer.id == note_in.customer_id, Customer.tenant_id == tenant_id)
    )
    if not cust_check.scalars().first():
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Generate sequence number
    count_stmt = select(DebitNote).join(Customer).where(Customer.tenant_id == tenant_id)
    res_count = await db.execute(count_stmt)
    total_notes = len(res_count.scalars().all())
    
    new_number = f"NC-{total_notes + 1:04d}" if note_in.type == 'Crédito' else f"ND-{total_notes + 1:04d}"

    new_note = DebitNote(
        **note_in.model_dump(),
        number=new_number,
        created_by_id=current_user.id,
        created_by_name=current_user.username
    )
    
    db.add(new_note)
    
    # --- AUTOMATIZACION CxC ---
    # Si la nota afecta una factura específica, actualizar su saldo
    if note_in.reference_invoice_id:
        ar_stmt = select(AccountsReceivable).where(
            AccountsReceivable.sale_id == note_in.reference_invoice_id,
            AccountsReceivable.tenant_id == tenant_id
        )
        ar_res = await db.execute(ar_stmt)
        ar_record = ar_res.scalars().first()
        
        if ar_record:
            if note_in.type == 'Débito':
                # Incrementa la deuda
                ar_record.remaining_amount += note_in.amount
                ar_record.total_amount += note_in.amount
                if ar_record.status == 'PAID':
                    ar_record.status = 'PARTIAL'
            elif note_in.type == 'Crédito':
                # Disminuye la deuda
                ar_record.remaining_amount -= note_in.amount
                if ar_record.remaining_amount <= 0:
                    ar_record.remaining_amount = 0
                    ar_record.status = 'PAID'
                elif ar_record.remaining_amount < ar_record.total_amount:
                    ar_record.status = 'PARTIAL'

    await db.commit()
    await db.refresh(new_note)
    
    # --- CONTABILIZACION AUTOMATICA (Journal Entry) ---
    try:
        # Check Tenant settings for accounting mode
        tenant_record = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant_obj = tenant_record.scalars().first()
        
        # Default is 'manual' per user request
        accounting_mode = tenant_obj.settings.get('accounting_mode', 'manual') if tenant_obj and tenant_obj.settings else 'manual'
        
        if accounting_mode == 'automatic':
            from app.services.accounting_service import AccountingService
            await AccountingService.account_commercial_note(db, new_note.id, str(tenant_id))
        else:
            print("Accounting mode is manual. Journal entry skipped.")
    except Exception as e:
        # Si falla la contabilización, no bloqueamos la creación de la nota
        print(f"Error contabilizando nota comercial: {e}")

    return new_note


# ─────────────────────────────────────────────────────────────────────────────
# Notas de Crédito Fiscales (SENIAT) con Items y Devolución a Inventario
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/credit-notes", response_model=CreditNoteResponse)
async def create_credit_note(
    note_in: CreditNoteCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales"))
):
    """
    Crea una Nota de Crédito fiscal formal vinculada a una Factura de Venta.
    - Soporta desglose por ítems devueltos/acreditados
    - Si restock_inventory es True, reingresa los productos al almacén de la venta
    - Disminuye el saldo pendiente en Cuentas por Cobrar (CxC)
    - Registra el número de control fiscal SENIAT
    """
    # 1. Validar que la venta exista y pertenezca al tenant
    sale_stmt = select(Sale).where(Sale.id == note_in.sale_id, Sale.tenant_id == tenant_id)
    sale_res = await db.execute(sale_stmt)
    sale = sale_res.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Factura de venta original no encontrada")

    # 2. Generar número correlativo de Nota de Crédito
    count_stmt = select(func.count(CreditNote.id)).where(CreditNote.tenant_id == tenant_id)
    count_res = await db.execute(count_stmt)
    total_cn = count_res.scalar() or 0
    generated_number = f"NC-{total_cn + 1:06d}"

    # 3. Crear cabecera de Nota de Crédito
    credit_note = CreditNote(
        number=generated_number,
        control_number=note_in.control_number,
        sale_id=sale.id,
        customer_id=note_in.customer_id,
        reason=note_in.reason,
        currency=note_in.currency or sale.currency,
        exchange_rate=note_in.exchange_rate or sale.exchange_rate,
        subtotal=note_in.subtotal,
        tax_total=note_in.tax_total,
        total=note_in.total,
        status="APPROVED",
        notes=note_in.notes,
        tenant_id=tenant_id,
        created_by_id=current_user.id,
        created_by_name=current_user.username
    )
    db.add(credit_note)
    await db.flush()  # Para obtener el ID

    # 4. Crear los ítems de la nota de crédito y reingresar stock si corresponde
    from app.services.wms_service import WMSService
    from app.domain.inventory import MovementType, MovementSubtype
    target_wh = sale.warehouse_id or 1

    for item in note_in.items:
        cn_item = CreditNoteItem(
            credit_note_id=credit_note.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
            tax_rate=item.tax_rate or Decimal('16.0000'),
            tax_amount=item.tax_amount or Decimal('0.0000'),
            total=item.total,
            tenant_id=tenant_id
        )
        db.add(cn_item)

        if note_in.restock_inventory and item.quantity > 0:
            try:
                await WMSService.register_movement(
                    db=db,
                    product_id=item.product_id,
                    warehouse_id=target_wh,
                    movement_type=MovementType.IN,
                    movement_subtype=MovementSubtype.ADJUSTMENT,
                    quantity=item.quantity,
                    reference=f"Reingreso por {generated_number} (Factura #{sale.id:06d})",
                    tenant_id=tenant_id,
                    user_id=current_user.id,
                    user_name=current_user.username,
                )
            except Exception as e:
                import logging
                logging.getLogger("nexus.sales").error(
                    f"Error reingresando stock para ítem {item.product_id} en NC {generated_number}: {e}"
                )

    # 5. Descontar saldo en Cuentas por Cobrar (CxC) si existe registro
    from app.domain.treasury import AccountsReceivable
    ar_stmt = select(AccountsReceivable).where(
        AccountsReceivable.sale_id == sale.id,
        AccountsReceivable.tenant_id == tenant_id
    )
    ar_res = await db.execute(ar_stmt)
    ar_record = ar_res.scalars().first()
    if ar_record:
        ar_record.remaining_amount -= note_in.total
        if ar_record.remaining_amount <= 0:
            ar_record.remaining_amount = Decimal('0.0000')
            ar_record.status = 'PAID'
        elif ar_record.remaining_amount < ar_record.total_amount:
            ar_record.status = 'PARTIAL'

    await db.commit()
    
    # Recargar con items
    full_stmt = select(CreditNote).where(CreditNote.id == credit_note.id).options(selectinload(CreditNote.items))
    final_res = await db.execute(full_stmt)
    return final_res.scalars().first()


@router.get("/credit-notes", response_model=List[CreditNoteResponse])
async def list_credit_notes(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    customer_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    _: bool = Depends(require_module("sales"))
):
    """Lista las Notas de Crédito emitidas por la empresa."""
    stmt = (
        select(CreditNote)
        .where(CreditNote.tenant_id == tenant_id)
        .options(selectinload(CreditNote.items))
        .order_by(CreditNote.created_at.desc())
    )
    if customer_id:
        stmt = stmt.where(CreditNote.customer_id == customer_id)
    stmt = stmt.limit(limit).offset(offset)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/credit-notes/{note_id}", response_model=CreditNoteResponse)
async def get_credit_note_detail(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    _: bool = Depends(require_module("sales"))
):
    """Detalle completo de una Nota de Crédito."""
    stmt = (
        select(CreditNote)
        .where(CreditNote.id == note_id, CreditNote.tenant_id == tenant_id)
        .options(selectinload(CreditNote.items))
    )
    res = await db.execute(stmt)
    note = res.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Nota de crédito no encontrada")
    return note

