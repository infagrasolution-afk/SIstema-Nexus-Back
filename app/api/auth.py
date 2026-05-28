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

# ─── Configuración de bloqueo ─────────────────────────────────────────────────
MAX_LOGIN_ATTEMPTS = 3
SUPPORT_WHATSAPP = "+58 412 016 1906"
SUPPORT_MESSAGE = (
    "Tu cuenta ha sido bloqueada por seguridad tras 3 intentos fallidos. "
    f"Contacta a soporte técnico por WhatsApp: {SUPPORT_WHATSAPP} "
    "para recuperar el acceso."
)


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

    # ── Usuario no existe ──────────────────────────────────────────────────────
    if not user:
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")

    # ── Cuenta bloqueada ───────────────────────────────────────────────────────
    if user.is_locked:
        if user.is_superuser:
            # Admin de empresa bloqueado → contactar soporte
            raise HTTPException(
                status_code=423,  # 423 Locked
                detail={
                    "type": "account_locked_admin",
                    "message": SUPPORT_MESSAGE,
                    "whatsapp": SUPPORT_WHATSAPP,
                    "whatsapp_link": f"https://wa.me/584120161906?text=Hola,%20necesito%20desbloquear%20mi%20cuenta%20de%20administrador%20en%20el%20ERP.%20Usuario:%20{user.username}",
                    "locked_at": user.locked_at.isoformat() if user.locked_at else None,
                }
            )
        else:
            # Usuario regular bloqueado → que contacte a su admin de empresa
            raise HTTPException(
                status_code=423,
                detail={
                    "type": "account_locked",
                    "message": "Tu cuenta está bloqueada. Contacta al administrador de tu empresa para desbloquearla.",
                    "locked_at": user.locked_at.isoformat() if user.locked_at else None,
                }
            )

    # ── Contraseña incorrecta ──────────────────────────────────────────────────
    if not verify_password(login_data.password, user.hashed_password):
        user.login_attempts = (user.login_attempts or 0) + 1
        attempts_left = MAX_LOGIN_ATTEMPTS - user.login_attempts

        if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.is_locked = True
            user.locked_at = datetime.utcnow()
            await db.commit()

            if user.is_superuser:
                raise HTTPException(
                    status_code=423,
                    detail={
                        "type": "account_locked_admin",
                        "message": SUPPORT_MESSAGE,
                        "whatsapp": SUPPORT_WHATSAPP,
                        "whatsapp_link": f"https://wa.me/584120161906?text=Hola,%20necesito%20desbloquear%20mi%20cuenta%20de%20administrador%20en%20el%20ERP.%20Usuario:%20{user.username}",
                    }
                )
            else:
                raise HTTPException(
                    status_code=423,
                    detail={
                        "type": "account_locked",
                        "message": "Cuenta bloqueada tras 3 intentos fallidos. Contacta al administrador de tu empresa.",
                    }
                )

        await db.commit()
        raise HTTPException(
            status_code=400,
            detail={
                "type": "wrong_password",
                "message": "Usuario o contraseña incorrectos",
                "attempts_left": attempts_left,
                "warning": f"⚠️ Te quedan {attempts_left} intento(s) antes de que tu cuenta sea bloqueada."
            }
        )

    # ── Login exitoso: resetear intentos ──────────────────────────────────────
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo. Contacta al administrador.")

    user.login_attempts = 0
    await db.flush()

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(user.id, user.tenant_id, expires_delta=access_expires)
    refresh_token = create_refresh_token(user.id, user.tenant_id, expires_delta=refresh_expires)

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

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == token_data.jti))
    stored = result.scalars().first()

    if stored is None or stored.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revocado o no encontrado")

    if not verify_password(refresh_token, stored.token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token no coincide")

    stored.revoked = True

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_access_token = create_access_token(int(token_data.sub), int(token_data.tenant_id), expires_delta=access_expires)
    new_refresh_token = create_refresh_token(int(token_data.sub), int(token_data.tenant_id), expires_delta=refresh_expires)

    new_refresh_payload = jwt.decode(new_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    new_hashed_rt = hash_token(new_refresh_token)

    db.add(RefreshToken(
        user_id=int(token_data.sub),
        jti=new_refresh_payload["jti"],
        token=new_hashed_rt,
        tenant_id=int(token_data.tenant_id),
        expires_at=datetime.utcnow() + refresh_expires,
        revoked=False
    ))
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
