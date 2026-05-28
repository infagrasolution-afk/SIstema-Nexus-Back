import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import init_tenant_db
from app.core.security import get_password_hash
from app.api.deps import get_current_user, get_master_db
from app.domain.user import User
from app.domain.tenant import Tenant
from app.schemas.tenant import TenantResponse, TenantBase, TenantUpdate
from app.schemas.user import UserResponse, UserCreate
from app.services.email_service import EmailService

router = APIRouter()

async def check_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superadmins can access this module")
    return current_user

@router.get("/dashboard")
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    total_tenants = (await db.execute(select(func.count(Tenant.id)))).scalar() or 0
    active_tenants = (await db.execute(select(func.count(Tenant.id)).where(Tenant.is_active == True))).scalar() or 0
    
    thirty_days_later = datetime.now() + timedelta(days=30)
    expiring_soon = (await db.execute(
        select(func.count(Tenant.id))
        .where(Tenant.subscription_end <= thirty_days_later)
        .where(Tenant.subscription_end >= datetime.now())
    )).scalar() or 0
    
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    
    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "expiring_soon": expiring_soon,
        "total_users": total_users,
    }

@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    result = await db.execute(select(Tenant))
    return result.scalars().all()

@router.post("/tenants", response_model=TenantResponse)
async def create_tenant(
    tenant_in: TenantBase,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    license_key = f"NX-{uuid.uuid4().hex[:12].upper()}"
    sub_end = datetime.now() + timedelta(days=365)
    
    new_tenant = Tenant(
        name=tenant_in.name, 
        email=tenant_in.email,
        tax_id=tenant_in.tax_id,
        license_key=license_key,
        subscription_end=sub_end,
        is_active=True,
        modules=tenant_in.modules or "sales,inventory,accounting"
    )
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    
    # AUTO-CREATE the tenant's private database file
    await init_tenant_db(new_tenant.id, new_tenant.name)
    
    # AUTO-CREATE the tenant's first admin user if provided
    if tenant_in.admin_username and tenant_in.admin_password:
        new_user = User(
            username=tenant_in.admin_username,
            email=tenant_in.email, # Use company email as default
            hashed_password=get_password_hash(tenant_in.admin_password),
            tenant_id=new_tenant.id,
            is_active=True,
            is_superuser=False, # Tenant admin is NOT a global superuser
            modules=new_tenant.modules
        )
        db.add(new_user)
        await db.commit()

    # Send Welcome Email
    if new_tenant.email:
        await EmailService.send_welcome_license(
            new_tenant.email, 
            new_tenant.name, 
            license_key, 
            sub_end.strftime("%Y-%m-%d")
        )
        
    return new_tenant

@router.put("/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant_global(
    tenant_id: int,
    tenant_in: TenantUpdate,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    for field, value in tenant_in.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
        
    await db.commit()
    await db.refresh(tenant)
    return tenant

@router.post("/tenants/{tenant_id}/renew", response_model=TenantResponse)
async def renew_tenant_license(
    tenant_id: int,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant.subscription_end = datetime.now() + timedelta(days=365)
    tenant.is_active = True
    
    await db.commit()
    await db.refresh(tenant)
    return tenant

@router.post("/tenants/check-licenses")
async def check_all_licenses(
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    result = await db.execute(select(Tenant).where(Tenant.is_active == True))
    tenants = result.scalars().all()
    
    notifications_sent = 0
    now = datetime.now()
    
    for tenant in tenants:
        if not tenant.subscription_end or not tenant.email:
            continue
            
        diff = tenant.subscription_end - now
        days_left = diff.days
        
        if days_left in [30, 15, 7, 3, 1]:
            await EmailService.send_license_warning(
                tenant.email, 
                tenant.name, 
                days_left, 
                tenant.license_key
            )
            notifications_sent += 1
            
    return {"message": f"License check completed. {notifications_sent} notifications sent."}

@router.post("/tenants/{tenant_id}/users", response_model=UserResponse)
async def create_tenant_admin(
    tenant_id: int,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        tenant_id=tenant_id,
        is_superuser=user_in.is_superuser,
        modules=user_in.modules
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ─────────────────────────────────────────────────────────────────────────────
# POST /users/{user_id}/unlock  — SOPORTE TÉCNICO (MONETIZADO POR WHATSAPP)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/users/{user_id}/unlock", response_model=UserResponse)
async def superadmin_unlock_and_reset(
    user_id: int,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    """
    Soporte Técnico (Monetizado): Desbloquea una cuenta de administrador de empresa.
    Tras recibir pago o soporte telefónico/WhatsApp, el dueño del software utiliza
    este endpoint para rehabilitar la cuenta de administrador.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_locked = False
    user.login_attempts = 0
    user.locked_at = None
    user.updated_by_id = admin.id
    user.updated_by_name = admin.username

    await db.commit()
    await db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# POST /users/{user_id}/reset-password-force  — Restablecer clave por superadmin
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/users/{user_id}/reset-password-force", response_model=UserResponse)
async def superadmin_reset_password_force(
    user_id: int,
    new_password: str,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin)
):
    """
    Soporte Técnico (Monetizado): Asigna una nueva contraseña temporal a un administrador.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.hashed_password = get_password_hash(new_password)
    user.is_locked = False
    user.login_attempts = 0
    user.locked_at = None
    user.updated_by_id = admin.id
    user.updated_by_name = admin.username

    await db.commit()
    await db.refresh(user)
    return user

