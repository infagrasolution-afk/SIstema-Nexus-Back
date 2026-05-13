from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from app.api.deps import get_current_user, get_master_db
from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    get_password_hash as hash_token, TokenPayload
)
from app.core.config import settings
from app.domain.user import User
from app.domain.refresh_token import RefreshToken
from app.schemas.auth import Token, Login, RefreshTokenRequest
from app.schemas.user import UserResponse

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/login", response_model=Token)
async def login_access_token(
    login_data: Login,
    db: AsyncSession = Depends(get_master_db)
):
    result = await db.execute(select(User).where(User.username == login_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
        
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(user.id, user.tenant_id, expires_delta=access_expires)
    refresh_token = create_refresh_token(user.id, user.tenant_id, expires_delta=refresh_expires)
    
    # Store hashed refresh token for revocation tracking
    refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    hashed_rt = hash_token(refresh_token)
    
    rt_entry = RefreshToken(
        user_id=user.id,
        jti=refresh_payload["jti"],
        token=hashed_rt,
        tenant_id=user.tenant_id,
        expires_at=datetime.utcnow() + refresh_expires,
        revoked=False
    )
    db.add(rt_entry)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tenant_id": user.tenant_id
    }

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_master_db)
):
    refresh_token = request.refresh_token
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.type != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")
        
    # Lookup stored refresh token entry
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == token_data.jti))
    stored = result.scalars().first()
    
    if stored is None or stored.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revocado o no encontrado")
        
    # Verify token matches stored hash
    if not verify_password(refresh_token, stored.token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token no coincide")
        
    # Revoke old token
    stored.revoked = True
    
    # Issue new tokens
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    new_access_token = create_access_token(int(token_data.sub), int(token_data.tenant_id), expires_delta=access_expires)
    new_refresh_token = create_refresh_token(int(token_data.sub), int(token_data.tenant_id), expires_delta=refresh_expires)
    
    # Save new refresh token
    new_refresh_payload = jwt.decode(new_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    new_hashed_rt = hash_token(new_refresh_token)
    
    new_rt_entry = RefreshToken(
        user_id=int(token_data.sub),
        jti=new_refresh_payload["jti"],
        token=new_hashed_rt,
        tenant_id=int(token_data.tenant_id),
        expires_at=datetime.utcnow() + refresh_expires,
        revoked=False
    )
    db.add(new_rt_entry)
    await db.commit()
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "tenant_id": int(token_data.tenant_id)
    }

@router.post("/logout")
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    refresh_token = request.refresh_token
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        
    if jti:
        result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        token_entry = result.scalars().first()
        if token_entry:
            token_entry.revoked = True
            await db.commit()
            
    return {"detail": "Sesión cerrada correctamente"}
