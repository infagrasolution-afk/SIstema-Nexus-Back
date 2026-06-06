from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.database import MasterSessionLocal, get_tenant_engine
from app.domain.user import User
from app.domain.tenant import Tenant
from app.domain.rbac import Role, RolePermission, Permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[int] = None

async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides a session to the MASTER database (users, tenants, licenses)."""
    async with MasterSessionLocal() as session:
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_master_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Authenticates the user against the master database."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[int] = Header(None),
    db: AsyncSession = Depends(get_master_db)
) -> int:
    """
    Determines which tenant the request is for.
    - Superadmin: Can specify X-Tenant-ID header to access ANY company.
    - Normal user: Always uses their own tenant_id. Header is ignored.
    """
    if x_tenant_id is not None and current_user.is_superuser:
        # Verify the tenant actually exists
        result = await db.execute(select(Tenant).where(Tenant.id == x_tenant_id))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Company not found")
        return x_tenant_id
    
    return current_user.tenant_id

async def get_db(
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[int] = Header(None),
    master_db: AsyncSession = Depends(get_master_db)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a session to the correct tenant database.
    - Superadmin + X-Tenant-ID header: connects to that company's DB.
    - Normal user: connects to their own company's DB.
    """
    # Determine which tenant to use
    if x_tenant_id is not None and current_user.is_superuser:
        result = await master_db.execute(select(Tenant).where(Tenant.id == x_tenant_id))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Company not found")
        target_tenant_id = x_tenant_id
        company_name = tenant.name
    else:
        target_tenant_id = current_user.tenant_id
        result = await master_db.execute(select(Tenant).where(Tenant.id == target_tenant_id))
        tenant = result.scalars().first()
        company_name = tenant.name if tenant else "Unknown"
    
    engine = get_tenant_engine(target_tenant_id, company_name)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

def require_permissions(required_permissions: list[str]):
    """
    Dependency to check if the current user has the required permissions.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_master_db)
    ):
        if current_user.is_superuser:
            return current_user
            
        if not current_user.role_id:
            raise HTTPException(status_code=403, detail="User has no role assigned")
            
        # Get permissions for the user's role
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == current_user.role_id)
        )
        result = await db.execute(stmt)
        user_permissions = [row[0] for row in result.all()]
        
        for perm in required_permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Not enough permissions. Required: {perm}"
                )
        return current_user
        
    return permission_checker

def require_module(module_name: str):
    """
    Dependency to check if the tenant has an active license for a module.
    """
    async def module_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_master_db)
    ):
        if current_user.is_superuser:
            return True
            
        result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
        tenant = result.scalars().first()
        
        if not tenant or not tenant.modules:
            raise HTTPException(status_code=403, detail="No hay módulos activos para esta empresa")
            
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        
        # Modules is a dict: {"sales": {"is_active": true, "expires_at": "..."}, ...}
        modules_info = tenant.modules if isinstance(tenant.modules, dict) else {}
        
        # Helper to check if a specific module is active and not expired
        def is_mod_active(mod_name):
            m = modules_info.get(mod_name, {})
            if not m.get("is_active", False):
                return False
            expires_at = m.get("expires_at")
            if not expires_at:
                return True # Legacy or permanent
            return expires_at > now

        # Logic for Administrativo (users)
        if module_name == "users":
            # If any OPERATIVE module is active, administrative is automatically active
            operative_modules = ["sales", "inventory", "accounting"]
            if any(is_mod_active(m) for m in operative_modules):
                return True
            # Otherwise, check administrative's own expiration
            if is_mod_active("users"):
                return True
            raise HTTPException(status_code=403, detail="La licencia del módulo Administrativo ha vencido")

        # Logic for Purchases (Compras y Proveedores)
        if module_name == "purchases":
            if is_mod_active("purchases") or is_mod_active("inventory") or is_mod_active("users"):
                return True
            raise HTTPException(status_code=403, detail="El módulo de Compras y Proveedores no está contratado o su licencia ha vencido")

        # Logic for Operative Modules
        if is_mod_active(module_name):
            return True
            
        raise HTTPException(status_code=403, detail=f"El módulo '{module_name}' no está contratado o su licencia ha vencido")
                
        return True
        
    return module_checker
