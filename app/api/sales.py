from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.api.deps import get_db, get_current_tenant
from app.services.sales_service import SalesService
from app.services.pdf_service import PDFService
from app.schemas.sales import SaleCreate, SaleResponse
from app.domain.sales import Sale

router = APIRouter()

@router.post("/", response_model=SaleResponse)
async def create_sale(
    sale_in: SaleCreate, 
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    try:
        return await SalesService.create_sale(db, sale_in, tenant_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
