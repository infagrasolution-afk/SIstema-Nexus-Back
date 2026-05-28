from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.api.deps import get_db, get_current_tenant, get_current_user, require_module
from app.services.sales_service import SalesService
from app.services.pdf_service import PDFService
from app.schemas.sales import SaleCreate, SaleResponse, BudgetCreate, BudgetResponse, CustomerCreate
from app.domain.sales import Sale, Budget, Customer
from app.domain.user import User

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
