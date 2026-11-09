import json
from datetime import datetime
from typing import AsyncGenerator, Optional, List, Dict, Any, Union
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

MODULE_LABELS = {
    "sales": "Ventas y Facturación",
    "pos": "Punto de Venta (POS)",
    "inventory": "Inventario y Almacenes (WMS)",
    "purchases": "Compras y Proveedores",
    "treasury": "Tesorería y Bancos",
    "cash": "Control de Caja",
    "accounting": "Contabilidad",
    "payroll": "Nómina y Recursos Humanos (LOTTT)",
    "hr": "Nómina y Recursos Humanos (LOTTT)",
    "fiscal": "Fiscal (Libros SENIAT)",
    "reports": "Reportes y Estadísticas",
    "users": "Administración de Usuarios",
    "settings": "Configuración Corporativa",
}


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    tenant_id: Optional[int] = None
    jti: Optional[str] = None
    type: Optional[str] = None
    session_id: Optional[str] = None


async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Proporciona una sesión a la base de datos MASTER (usuarios, empresas, licencias)."""
    async with MasterSessionLocal() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_master_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Autentica al usuario actual contra la base de datos principal y valida su sesión."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no válidas o sesión caducada. Por favor, inicia sesión nuevamente.",
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Tu cuenta de usuario ha sido desactivada. Consulta con el administrador."
        )

    # Control de sesión única: si el usuario inició sesión en otro navegador/equipo, invalida la previa
    token_session_id = token_data.session_id or payload.get("session_id")
    if token_session_id and user.active_session_id and token_session_id != user.active_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SESSION_SUPERSEDED: Tu cuenta ha sido abierta en otro dispositivo o navegador. Se ha cerrado esta sesión automáticamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[int] = Header(None),
    db: AsyncSession = Depends(get_master_db)
) -> int:
    """
    Determina la empresa (tenant) de la petición:
    - Superadmin global: puede indicar X-Tenant-ID para navegar entre empresas.
    - Usuario regular o admin de empresa: opera siempre en su propio tenant_id.
    """
    if x_tenant_id is not None and current_user.is_superuser:
        result = await db.execute(select(Tenant).where(Tenant.id == x_tenant_id))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        return x_tenant_id

    return current_user.tenant_id


async def get_db(
    current_user: User = Depends(get_current_user),
    x_tenant_id: Optional[int] = Header(None),
    master_db: AsyncSession = Depends(get_master_db)
) -> AsyncGenerator[AsyncSession, None]:
    """
    Proporciona una sesión a la base de datos y esquema del tenant correspondiente.
    """
    if x_tenant_id is not None and current_user.is_superuser:
        result = await master_db.execute(select(Tenant).where(Tenant.id == x_tenant_id))
        tenant = result.scalars().first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
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


def require_permissions(required_permissions: List[str]):
    """
    Verifica que el usuario posea los permisos necesarios para ejecutar la acción.
    Los administradores de la empresa y superusuarios tienen permiso total.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_master_db)
    ):
        # Superadmin global y administradores de empresa tienen acceso completo
        if current_user.is_superuser or getattr(current_user, "is_tenant_admin", False):
            return current_user

        if not current_user.role_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Tu usuario no tiene un rol asignado en la empresa. Solicita a tu administrador que te asigne uno."
            )

        # Cargar los permisos del rol del usuario
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == current_user.role_id)
        )
        result = await db.execute(stmt)
        user_permissions = set(row[0] for row in result.all())

        for perm in required_permissions:
            if perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail=f"No dispones del permiso requerido ({perm}) para realizar esta acción. Consulta con el administrador."
                )
        return current_user

    return permission_checker


def _normalize_modules(raw: Any) -> Dict[str, Any]:
    """Parsea el campo modules de Tenant (soporta dict, list, JSON str) a un diccionario estándar."""
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}
    if isinstance(raw, list):
        return {str(m): {"is_active": True} for m in raw}
    if isinstance(raw, dict):
        normalized = {}
        for k, v in raw.items():
            if isinstance(v, bool):
                normalized[k] = {"is_active": v}
            elif isinstance(v, dict):
                normalized[k] = v
            else:
                normalized[k] = {"is_active": bool(v)}
        return normalized
    return {}


def require_module(module_name: str):
    """
    Valida que la empresa tenga contratado y activo el módulo especificado.
    Superadministradores y empresas Demo/Master no tienen restricción.
    """
    async def module_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_master_db)
    ):
        if current_user.is_superuser:
            return True

        result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
        tenant = result.scalars().first()

        if not tenant:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

        # Tenant 1 (Master) siempre tiene todo activo
        if tenant.id == 1:
            return True

        # Validar si la licencia general de la empresa venció
        now_dt = datetime.now()
        if tenant.subscription_end and tenant.subscription_end < now_dt:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La suscripción general del sistema para su empresa ha vencido. Contacte a soporte técnico para renovarla."
            )

        modules_dict = _normalize_modules(tenant.modules)
        now_str = now_dt.isoformat()

        def is_mod_active(mod: str) -> bool:
            m = modules_dict.get(mod, {})
            if not m.get("is_active", False):
                return False
            expires_at = m.get("expires_at")
            if not expires_at:
                return True
            return expires_at > now_str

        # Mapeo de alias y dependencias
        if module_name in ("cash", "pos"):
            # Caja y POS forman parte de Ventas
            if is_mod_active("sales") or is_mod_active("pos"):
                return True
        elif module_name in ("fiscal",):
            # Fiscal se activa si tiene Ventas o Contabilidad
            if is_mod_active("sales") or is_mod_active("accounting"):
                return True
        elif module_name in ("payroll", "hr"):
            if is_mod_active("payroll") or is_mod_active("hr"):
                return True
        elif module_name == "purchases":
            if is_mod_active("purchases") or is_mod_active("inventory"):
                return True
        elif module_name == "users":
            # Si tiene ventas, inventario o contabilidad, administrativo está activo
            if any(is_mod_active(m) for m in ("sales", "inventory", "accounting", "users", "admin")):
                return True
        elif is_mod_active(module_name):
            return True

        label = MODULE_LABELS.get(module_name, module_name)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El módulo de {label} no está incluido en su plan o su licencia ha vencido."
        )

    return module_checker
