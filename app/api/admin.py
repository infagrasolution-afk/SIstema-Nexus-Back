import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import init_tenant_db, set_tenant_custom_db_cache
from app.core.security import get_password_hash
from app.api.deps import get_current_user, get_master_db
from app.domain.user import User
from app.domain.tenant import Tenant
from app.domain.security_audit_log import SecurityAuditLog
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
    total_audit_events = 0
    try:
        total_audit_events = (await db.execute(select(func.count(SecurityAuditLog.id)))).scalar() or 0
    except Exception:
        pass

    # Conteo de usuarios por tenant para vista ejecutiva del dueño del sistema
    users_by_tenant_res = await db.execute(
        select(User.tenant_id, func.count(User.id)).group_by(User.tenant_id)
    )
    users_per_tenant = {str(r[0]): r[1] for r in users_by_tenant_res.all()}
    
    return {
        "total_tenants": total_tenants,
        "active_tenants": active_tenants,
        "expiring_soon": expiring_soon,
        "total_users": total_users,
        "total_audit_events": total_audit_events,
        "users_per_tenant": users_per_tenant,
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
        modules=tenant_in.modules or "sales,inventory,accounting",
        custom_database_url=(tenant_in.custom_database_url or "").strip() or None,
    )
    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)
    
    # AUTO-CREATE the tenant's schema in shared pool OR tables in dedicated DB (Hybrid mode)
    await init_tenant_db(new_tenant.id, new_tenant.name, new_tenant.custom_database_url)
    
    # AUTO-CREATE the tenant's first admin user if provided
    if tenant_in.admin_username and tenant_in.admin_password:
        user_modules = ",".join(new_tenant.modules.keys()) if isinstance(new_tenant.modules, dict) else str(new_tenant.modules)
        new_user = User(
            username=tenant_in.admin_username,
            email=tenant_in.email, # Use company email as default
            hashed_password=get_password_hash(tenant_in.admin_password),
            tenant_id=new_tenant.id,
            is_active=True,
            is_superuser=False, # Tenant admin is NOT a global superuser
            is_tenant_admin=True,
            modules=user_modules
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
        
    update_data = tenant_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    # Si se actualizaron los módulos contratados del cliente, sincronizar los permisos de su usuario admin
    if "modules" in update_data and update_data["modules"] is not None:
        raw_mods = update_data["modules"]
        if isinstance(raw_mods, dict):
            active_keys = [
                k for k, v in raw_mods.items()
                if (isinstance(v, dict) and v.get("is_active", True)) or v is True
            ]
        elif isinstance(raw_mods, list):
            active_keys = [str(x) for x in raw_mods]
        else:
            active_keys = [x.strip() for x in str(raw_mods).split(",") if x.strip()]
        mods_csv = ",".join(active_keys)

        users_res = await db.execute(
            select(User).where(User.tenant_id == tenant_id, User.role == "admin")
        )
        for u in users_res.scalars().all():
            u.modules = mods_csv
        
    await db.commit()
    await db.refresh(tenant)
    set_tenant_custom_db_cache(tenant.id, getattr(tenant, "custom_database_url", None))
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
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        tenant_id=tenant_id,
        is_superuser=user_in.is_superuser or False,
        is_tenant_admin=True,
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
    user.active_session_id = None
    user.updated_by_id = admin.id
    user.updated_by_name = admin.username

    await db.commit()
    await db.refresh(user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# GET /security-audit-logs — BITÁCORA FORENSE GLOBAL (USUARIO, IP, ACCIÓN)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/security-audit-logs")
async def get_global_security_audit_logs(
    limit: int = 200,
    tenant_id: int = None,
    db: AsyncSession = Depends(get_master_db),
    admin: User = Depends(check_admin),
):
    """
    Devuelve la bitácora forense inmutable de seguridad de todo el ecosistema SaaS:
    Usuario, Empresa, Dirección IP, Dispositivo (User-Agent), Módulo, Acción, Ruta y Payload.
    """
    stmt = select(SecurityAuditLog).order_by(SecurityAuditLog.created_at.desc()).limit(limit)
    if tenant_id is not None:
        stmt = stmt.where(SecurityAuditLog.tenant_id == tenant_id)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "id": l.id,
            "created_at": l.created_at,
            "tenant_id": l.tenant_id,
            "user_id": l.user_id,
            "username": l.username or "Anónimo / Sistema",
            "ip_address": l.ip_address or "N/A",
            "user_agent": l.user_agent or "N/A",
            "module": l.module,
            "action": l.action,
            "http_method": l.http_method,
            "endpoint_path": l.endpoint_path,
            "status_code": l.status_code,
            "payload_summary": l.payload_summary,
        }
        for l in logs
    ]


