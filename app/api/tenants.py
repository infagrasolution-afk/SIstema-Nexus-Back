from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_current_tenant, get_master_db
from app.domain.tenant import Tenant
from app.schemas.tenant import TenantUpdate, TenantResponse

router = APIRouter()

@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.get("/branches", response_model=List[TenantResponse])
async def list_my_branches(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant)
):
    # Find branches where parent_id is the current tenant
    result = await db.execute(select(Tenant).where(Tenant.parent_id == tenant_id))
    return result.scalars().all()

@router.put("/me", response_model=TenantResponse)
async def update_my_tenant(
    tenant_in: TenantUpdate,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    for field, value in tenant_in.model_dump().items():
        setattr(tenant, field, value)
    
    await db.commit()
    await db.refresh(tenant)
    return tenant
