from datetime import datetime, timedelta
import hashlib
import uuid
from typing import Dict, List
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

import os
from app.api.deps import get_current_user, get_master_db
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token,
    TokenPayload
)
from app.core.config import settings
from app.core.network import extract_client_ip
from app.core.totp import generate_totp_secret, verify_totp_code, build_otpauth_uri
from app.domain.user import User
from app.domain.refresh_token import RefreshToken
from app.schemas.auth import Token, Login, RefreshTokenRequest, ChangePasswordRequest, TOTPVerifyRequest
from app.schemas.user import UserResponse

router = APIRouter()

# ─── Configuración de Seguridad y Soporte ─────────────────────────────────────
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOCKOUT_MINUTES = settings.LOCKOUT_MINUTES
SUPPORT_WHATSAPP = "+58 412 016 1906"
SUPPORT_MESSAGE = (
    "Tu cuenta ha sido bloqueada temporalmente tras varios intentos fallidos por seguridad. "
    f"Si eres administrador, puedes contactar a soporte técnico oficial por WhatsApp: {SUPPORT_WHATSAPP} "
    "o esperar el tiempo de desbloqueo automático."
)

# In-memory rate limiting por IP (limpia intentos viejos en cada llamada)
_ip_attempts: Dict[str, List[datetime]] = defaultdict(list)


def _check_ip_rate_limit(client_ip: str) -> None:
    now = datetime.utcnow()
    window = timedelta(seconds=settings.LOGIN_RATE_WINDOW_SECONDS)
    # Filtrar solo intentos dentro de la ventana de tiempo
    attempts = [t for t in _ip_attempts[client_ip] if now - t < window]
    _ip_attempts[client_ip] = attempts

    if len(attempts) >= settings.LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Demasiados intentos de acceso desde esta conexión. "
                "Por tu seguridad, espera unos minutos antes de volver a intentar."
            )
        )
    _ip_attempts[client_ip].append(now)


@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_user)):
    """Retorna la información del usuario autenticado."""
    return current_user


@router.post("/login", response_model=Token)
async def login_access_token(
    login_data: Login,
    request: Request,
    db: AsyncSession = Depends(get_master_db)
):
    # Validar límite de intentos por dirección IP real (detrás de proxy Render/Cloudflare)
    client_ip = extract_client_ip(request)
    _check_ip_rate_limit(client_ip)

    username_clean = (login_data.username or "").strip()
    result = await db.execute(select(User).where(User.username == username_clean))
    user = result.scalars().first()

    # ── Usuario no existe ──────────────────────────────────────────────────────
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Nombre de usuario o contraseña incorrectos"
        )

    # ── Cuenta bloqueada (con expiración temporal automática) ──────────────────
    if user.is_locked:
        now = datetime.utcnow()
        lock_time = user.locked_at.replace(tzinfo=None) if user.locked_at else None
        lockout_delta = timedelta(minutes=LOCKOUT_MINUTES)

        # Si ya transcurrió el tiempo de penalización, desbloquear automáticamente
        if lock_time and (now - lock_time) >= lockout_delta:
            user.is_locked = False
            user.login_attempts = 0
            user.locked_at = None
            await db.commit()
        else:
            time_left_min = int((lockout_delta - (now - lock_time)).total_seconds() / 60) if lock_time else LOCKOUT_MINUTES
            time_left_str = f" Podrás reintentar en aproximadamente {max(1, time_left_min)} minuto(s)."

            if user.is_superuser:
                raise HTTPException(
                    status_code=423,  # 423 Locked
                    detail={
                        "type": "account_locked_admin",
                        "message": SUPPORT_MESSAGE + time_left_str,
                        "whatsapp": SUPPORT_WHATSAPP,
                        "whatsapp_link": f"https://wa.me/584120161906?text=Hola,%20necesito%20desbloquear%20mi%20cuenta%20de%20administrador%20en%20el%20ERP.%20Usuario:%20{user.username}",
                        "locked_at": user.locked_at.isoformat() if user.locked_at else None,
                    }
                )
            else:
                raise HTTPException(
                    status_code=423,
                    detail={
                        "type": "account_locked",
                        "message": (
                            "Tu cuenta se encuentra bloqueada por seguridad tras 3 intentos fallidos."
                            + time_left_str
                            + " O solicita al administrador de tu empresa que la desbloquee de inmediato."
                        ),
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
                        "message": (
                            f"Cuenta bloqueada por seguridad tras {MAX_LOGIN_ATTEMPTS} intentos fallidos. "
                            f"Se desbloqueará automáticamente en {LOCKOUT_MINUTES} minutos o puedes solicitar al administrador de tu empresa que la reactive."
                        ),
                    }
                )

        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "wrong_password",
                "message": "Usuario o contraseña incorrectos",
                "attempts_left": attempts_left,
                "warning": f"⚠️ Te quedan {attempts_left} intento(s) antes del bloqueo temporal de tu cuenta."
            }
        )

    # ── Login exitoso: validar estado, 2FA y generar sesión activa ────────────
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tu usuario está inactivo en el sistema. Contacta al administrador de la empresa."
        )

    if getattr(user, "totp_enabled", False) and getattr(user, "totp_secret", None):
        if not login_data.totp_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "2fa_required",
                    "message": "Ingresa el código de 6 dígitos de tu aplicación Google Authenticator.",
                },
            )
        if not verify_totp_code(user.totp_secret, login_data.totp_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "invalid_2fa",
                    "message": "Código 2FA inválido o expirado. Verifica tu aplicación Google Authenticator.",
                },
            )

    user.login_attempts = 0
    # Generar sesión única activa: cualquier otra sesión previa en otra máquina queda invalidada
    new_session_id = str(uuid.uuid4())
    user.active_session_id = new_session_id
    await db.flush()

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        user.id, user.tenant_id, expires_delta=access_expires, session_id=new_session_id
    )
    refresh_token = create_refresh_token(
        user.id, user.tenant_id, expires_delta=refresh_expires, session_id=new_session_id
    )

    refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    hashed_rt = hashlib.sha256(refresh_token.encode()).hexdigest()

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
            raise HTTPException(status_code=400, detail="Tipo de token no válido para renovación")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El token de actualización ha expirado o no es válido")

    # Verificar si el usuario existe y si su sesión sigue vigente
    user_res = await db.execute(select(User).where(User.id == int(token_data.sub)))
    user = user_res.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="SESSION_SUPERSEDED: Usuario no disponible o sesión cerrada."
        )

    # Si el usuario tiene una sesión activa diferente, esta sesión se cierra
    if token_data.session_id and user.active_session_id and token_data.session_id != user.active_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SESSION_SUPERSEDED: Tu sesión ha sido abierta en otro dispositivo. Se ha cerrado esta sesión automáticamente."
        )

    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == token_data.jti))
    stored = result.scalars().first()

    if stored is None or stored.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El token de actualización ha sido revocado o ya no es válido")

    # Validación de token
    token_sha = hashlib.sha256(refresh_token.encode()).hexdigest()
    is_valid = False
    if stored.token == token_sha:
        is_valid = True
    elif stored.token.startswith("$2b$") or stored.token.startswith("$2a$"):
        is_valid = verify_password(refresh_token, stored.token)

    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de actualización no coincide")

    stored.revoked = True

    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    current_sid = user.active_session_id or token_data.session_id
    new_access_token = create_access_token(
        int(token_data.sub), int(token_data.tenant_id), expires_delta=access_expires, session_id=current_sid
    )
    new_refresh_token = create_refresh_token(
        int(token_data.sub), int(token_data.tenant_id), expires_delta=refresh_expires, session_id=current_sid
    )

    new_refresh_payload = jwt.decode(new_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    new_hashed_rt = hashlib.sha256(new_refresh_token.encode()).hexdigest()

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no válido")

    if jti:
        result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        token_entry = result.scalars().first()
        if token_entry:
            token_entry.revoked = True
            await db.commit()

    return {"detail": "Sesión cerrada correctamente"}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    if len(payload.new_password or "") < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres.")

    result = await db.execute(select(User).where(User.id == current_user.id))
    user_db = result.scalars().first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user_db.hashed_password = get_password_hash(payload.new_password)
    await db.commit()
    return {"detail": "Contraseña actualizada exitosamente."}


@router.post("/2fa/setup")
async def setup_2fa(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user),
):
    secret = generate_totp_secret()
    result = await db.execute(select(User).where(User.id == current_user.id))
    user_db = result.scalars().first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user_db.totp_secret = secret
    user_db.totp_enabled = False
    await db.commit()
    uri = build_otpauth_uri(user_db.username, secret, issuer="APEX ERP")
    return {"secret": secret, "otpauth_uri": uri}


@router.post("/2fa/enable")
async def enable_2fa(
    payload: TOTPVerifyRequest,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user_db = result.scalars().first()
    if not user_db or not user_db.totp_secret:
        raise HTTPException(status_code=400, detail="Primero genera el código QR de configuración 2FA.")
    if not verify_totp_code(user_db.totp_secret, payload.code):
        raise HTTPException(status_code=400, detail="Código de 6 dígitos incorrecto o expirado. Inténtalo de nuevo.")
    user_db.totp_enabled = True
    await db.commit()
    return {"detail": "Autenticación de 2 Factores (2FA) activada exitosamente.", "totp_enabled": True}


@router.post("/2fa/disable")
async def disable_2fa(
    payload: TOTPVerifyRequest,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == current_user.id))
    user_db = result.scalars().first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if payload.password and not verify_password(payload.password, user_db.hashed_password):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta.")
    if user_db.totp_enabled and user_db.totp_secret and not verify_totp_code(user_db.totp_secret, payload.code):
        raise HTTPException(status_code=400, detail="Código 2FA inválido.")
    user_db.totp_enabled = False
    user_db.totp_secret = None
    await db.commit()
    return {"detail": "Autenticación de 2 Factores (2FA) desactivada.", "totp_enabled": False}


@router.get("/security-status")
async def get_security_status(current_user: User = Depends(get_current_user)):
    raw_secret = (os.getenv("SECRET_KEY") or "").strip()
    secret_ok = len(raw_secret) >= 32
    return {
        "totp_enabled": bool(getattr(current_user, "totp_enabled", False)),
        "is_superuser": bool(current_user.is_superuser),
        "secret_key_configured": secret_ok if current_user.is_superuser else True,
        "proxy_ip_rate_limit": True,
    }
