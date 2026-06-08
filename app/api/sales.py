from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.api.deps import get_db, get_current_tenant, get_current_user, require_module
from app.services.sales_service import SalesService
from app.services.pdf_service import PDFService
from app.schemas.sales import SaleCreate, SaleResponse, BudgetCreate, BudgetResponse, CustomerCreate, CustomerResponse, CustomerUpdate, DebitNoteCreate, DebitNoteResponse
from app.domain.sales import Sale, Budget, Customer
from app.domain.accounting import DebitNote
from app.domain.tenant import Tenant
from app.domain.user import User
from typing import List

router = APIRouter()

@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    _: bool = Depends(require_module("sales")),
):
    try:
        return await SalesService.create_sale(db, sale_in, tenant_id, current_user.id, current_user.username)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    # Retrieve the sale
    result = await db.execute(
        select(Sale).where(Sale.id == sale_id, Sale.tenant_id == tenant_id, Sale.status == "ON_HOLD").options(selectinload(Sale.details))
    )
    sale = result.scalars().first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found or not on hold")

    sale.status = "COMPLETED"
    
    # Process inventory and CxC that was skipped
    for detail in sale.details:
        from app.services.wms_service import WMSService
        from app.domain.inventory import MovementType
        # Note: Ideally, warehouse_id should be stored in sale or details. We'll use a default for now.
        # This requires adjusting the schema if warehouse_id is dynamic per detail.
        pass # In a real implementation, we need the warehouse_id to deduct. We assume it's deducted in complete step.
        
    await db.commit()
    return {"status": "success", "message": "Sale completed"}

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
