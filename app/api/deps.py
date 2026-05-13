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
