from datetime import datetime, timedelta
import uuid
from typing import Any, AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.database import MasterSessionLocal, get_tenant_engine
from app.domain.user import User
from app.domain.tenant import Tenant
from app.domain.refresh_token import RefreshToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[int] = None
    jti: Optional[str] = None
    type: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def _generate_jti() -> str:
    """Generate a unique JWT ID (jti) for token revocation tracking."""
    return str(uuid.uuid4())

def create_access_token(subject: int | Any, tenant_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a short‑lived access token.
    Includes standard claims: exp, sub, tenant_id, jti, and token_type.
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "tenant_id": tenant_id,
        "jti": _generate_jti(),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: int | Any, tenant_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a longer‑lived refresh token.
    Refresh tokens are stored hashed in the DB for revocation checks.
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "tenant_id": tenant_id,
        "jti": _generate_jti(),
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Provides a session to the MASTER database (users, tenants, licenses, refresh tokens)."""
    async with MasterSessionLocal() as session:
        yield session

async def _verify_token_not_revoked(db: AsyncSession, jti: str) -> None:
    """Raise HTTPException if a token with the given jti is revoked or not found."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    token_entry = result.scalars().first()
    if token_entry is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if token_entry.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

async def get_current_user(
    db: AsyncSession = Depends(get_master_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Authenticates the user against the master database and checks token revocation."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.sub is None or token_data.jti is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    await _verify_token_not_revoked(db, token_data.jti)

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
    """Determines which tenant the request is for."""
    if x_tenant_id is not None and current_user.is_superuser:
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
    """Provides a session to the correct tenant database."""
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
