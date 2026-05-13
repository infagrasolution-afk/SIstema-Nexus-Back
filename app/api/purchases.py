from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db, get_current_tenant
from app.services.purchase_service import PurchaseService
from app.schemas.purchases import PurchaseCreate, PurchaseResponse

router = APIRouter()

@router.post("/", response_model=PurchaseResponse)
async def create_purchase(
    purchase_in: PurchaseCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    try:
        return await PurchaseService.create_purchase(db, purchase_in, tenant_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[PurchaseResponse])
async def get_purchases(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    from app.domain.purchases import Purchase
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(Purchase)
        .where(Purchase.tenant_id == tenant_id)
        .options(selectinload(Purchase.details))
    )
    return result.scalars().all()
