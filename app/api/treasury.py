from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.api.deps import get_db, get_current_tenant
from app.domain.treasury import AccountsReceivable, AccountsPayable, TreasuryPayment
from app.schemas.treasury import (
    AccountsReceivableResponse, AccountsPayableResponse, 
    TreasuryPaymentCreate, TreasuryPaymentResponse
)
from app.services.treasury_service import TreasuryService

router = APIRouter()

@router.get("/ar", response_model=List[AccountsReceivableResponse])
async def get_ar_list(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(AccountsReceivable)
        .where(AccountsReceivable.tenant_id == tenant_id)
        .options(selectinload(AccountsReceivable.customer), selectinload(AccountsReceivable.payments))
    )
    return result.scalars().all()

@router.get("/ap", response_model=List[AccountsPayableResponse])
async def get_ap_list(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(
        select(AccountsPayable)
        .where(AccountsPayable.tenant_id == tenant_id)
        .options(selectinload(AccountsPayable.supplier), selectinload(AccountsPayable.payments))
    )
    return result.scalars().all()

@router.post("/payments", response_model=TreasuryPaymentResponse)
async def create_payment(
    payment_in: TreasuryPaymentCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant)
):
    return await TreasuryService.process_payment(db, payment_in, tenant_id)
