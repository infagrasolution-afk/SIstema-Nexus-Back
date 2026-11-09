from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.api.deps import get_current_tenant, get_master_db, get_current_user
from app.domain.tenant import Tenant
from app.domain.user import User
from app.schemas.tenant import TenantProfileUpdate, TenantResponse

router = APIRouter()

@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return tenant

@router.get("/branches", response_model=List[TenantResponse])
async def list_my_branches(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant)
):
    result = await db.execute(select(Tenant).where(Tenant.parent_id == tenant_id))
    return result.scalars().all()

@router.put("/me", response_model=TenantResponse)
async def update_my_tenant(
    tenant_in: TenantProfileUpdate,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Permite al administrador de la empresa actualizar sus datos visuales y de contacto.
    Los módulos contratados y licencias están protegidos contra manipulación.
    """
    is_admin = current_user.is_superuser or getattr(current_user, 'is_tenant_admin', False)
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador de la empresa puede modificar la información y configuración corporativa."
        )

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Solo actualizar los campos explícitamente enviados en TenantProfileUpdate
    update_data = tenant_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant
