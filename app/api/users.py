from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.api.deps import get_current_user, get_current_tenant, get_master_db
from app.core.security import get_password_hash
from app.domain.user import User
from app.domain.rbac import Role, Permission, RolePermission
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()


def _is_tenant_admin(current_user: User, tenant_id: int) -> bool:
    """Un usuario es admin de su tenant si pertenece a él y tiene módulos asignados."""
    return current_user.tenant_id == tenant_id and current_user.modules is not None


async def _load_user_role(db: AsyncSession, user: User) -> dict:
    """Carga el rol y sus permisos para incluirlos en la respuesta."""
    if not user.role_id:
        return None
    result = await db.execute(
        select(Role).where(Role.id == user.role_id)
    )
    role = result.scalars().first()
    if not role:
        return None
    # Cargar permisos del rol
    perms_result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    )
    role.permissions = perms_result.scalars().all()
    return role


# ─────────────────────────────────────────────────────────────────────────────
# GET /users/  — Listar usuarios del tenant
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """Lista todos los usuarios de la empresa con su rol y permisos."""
    if not current_user.is_superuser and not _is_tenant_admin(current_user, tenant_id):
        raise HTTPException(status_code=403, detail="Sin permisos para listar usuarios")

    result = await db.execute(select(User).where(User.tenant_id == tenant_id))
    users = result.scalars().all()

    # Cargar el rol de cada usuario
    for user in users:
        user.role = await _load_user_role(db, user)

    return users


# ─────────────────────────────────────────────────────────────────────────────
# GET /users/roles  — Listar roles disponibles del tenant (para el formulario)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/roles")
async def get_available_roles(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """Retorna los roles del tenant disponibles para asignar a usuarios."""
    if not current_user.is_superuser and not _is_tenant_admin(current_user, tenant_id):
        raise HTTPException(status_code=403, detail="Sin permisos")

    result = await db.execute(
        select(Role).where(Role.tenant_id == tenant_id)
    )
    roles = result.scalars().all()
    for role in roles:
        perms_result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
        role.permissions = perms_result.scalars().all()
    return roles


# ─────────────────────────────────────────────────────────────────────────────
# GET /users/permissions  — Listar todos los permisos del sistema
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/permissions")
async def get_all_permissions(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna todos los permisos disponibles del sistema, agrupados por módulo."""
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    permissions = result.scalars().all()

    # Agrupar por módulo para facilitar el frontend
    grouped: dict = {}
    for perm in permissions:
        mod = perm.module
        if mod not in grouped:
            grouped[mod] = []
        grouped[mod].append({
            "id": perm.id,
            "code": perm.code,
            "description": perm.description,
            "module": perm.module
        })
    return grouped


# ─────────────────────────────────────────────────────────────────────────────
# POST /users/  — Crear usuario con rol y/o permisos
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo usuario dentro de la empresa.

    El admin de la empresa puede:
    - Asignar un **rol existente** (`role_id`) → el usuario hereda todos los permisos del rol
    - Especificar los **módulos** que puede ver (`modules`: "sales,inventory")
    - El superadmin global puede crear admins; el admin de empresa no puede crear superadmins globales
    """
    if not current_user.is_superuser and not _is_tenant_admin(current_user, tenant_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear usuarios. Contacta al administrador."
        )

    # El admin de tenant NO puede crear superadmins globales
    final_is_superuser = user_in.is_superuser if current_user.is_superuser else False

    # Verificar que el username no exista
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail=f"El usuario '{user_in.username}' ya existe")

    # Validar que el role_id pertenece al mismo tenant (si se envía)
    if user_in.role_id:
        role_check = await db.execute(
            select(Role).where(Role.id == user_in.role_id, Role.tenant_id == tenant_id)
        )
        if not role_check.scalars().first():
            raise HTTPException(status_code=400, detail="El rol seleccionado no existe en esta empresa")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active if user_in.is_active is not None else True,
        is_superuser=final_is_superuser,
        tenant_id=tenant_id,
        modules=user_in.modules,
        role_id=user_in.role_id,
        created_by_id=current_user.id,
        created_by_name=current_user.username,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Cargar el rol para la respuesta
    new_user.role = await _load_user_role(db, new_user)
    return new_user


# ─────────────────────────────────────────────────────────────────────────────
# PUT /users/{user_id}  — Actualizar usuario (incluyendo cambio de rol)
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza un usuario de la empresa.
    - Admin puede cambiar el rol, módulos, contraseña y estado activo de cualquier usuario.
    - Un usuario normal solo puede cambiar su propia contraseña/email.
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    is_admin = current_user.is_superuser or _is_tenant_admin(current_user, tenant_id)
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar este usuario")

    # Campos que solo el admin puede cambiar
    if is_admin:
        if user_in.modules is not None:
            user.modules = user_in.modules
        if user_in.is_active is not None:
            user.is_active = user_in.is_active
        if user_in.role_id is not None:
            # Validar que el rol es del mismo tenant
            role_check = await db.execute(
                select(Role).where(Role.id == user_in.role_id, Role.tenant_id == tenant_id)
            )
            if not role_check.scalars().first():
                raise HTTPException(status_code=400, detail="El rol seleccionado no existe en esta empresa")
            user.role_id = user_in.role_id
        # Si el admin lo edita, reseteamos el bloqueo automáticamente por conveniencia
        user.is_locked = False
        user.login_attempts = 0
        user.locked_at = None

    # Campos que cualquiera puede cambiar en sí mismo
    if user_in.username is not None:
        user.username = user_in.username
    if user_in.email is not None:
        user.email = user_in.email
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)
        # Si el propio usuario cambia su contraseña, se asume desbloqueo si estuviese bloqueado
        user.is_locked = False
        user.login_attempts = 0
        user.locked_at = None

    user.updated_by_id = current_user.id
    user.updated_by_name = current_user.username

    await db.commit()
    await db.refresh(user)
    user.role = await _load_user_role(db, user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# POST /users/{user_id}/unlock  — Desbloquear usuario manualmente
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/{user_id}/unlock", response_model=UserResponse)
async def unlock_user(
    user_id: int,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Desbloquea una cuenta de usuario de la empresa que fue bloqueada tras 3 intentos.
    Solo puede ser realizado por el administrador de la empresa.
    """
    if not current_user.is_superuser and not _is_tenant_admin(current_user, tenant_id):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para desbloquear usuarios de esta empresa."
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_locked = False
    user.login_attempts = 0
    user.locked_at = None
    user.updated_by_id = current_user.id
    user.updated_by_name = current_user.username

    await db.commit()
    await db.refresh(user)
    user.role = await _load_user_role(db, user)
    return user


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /users/{user_id}  — Desactivar usuario (soft delete)
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """Desactiva un usuario (no lo elimina físicamente)."""
    if not current_user.is_superuser and not _is_tenant_admin(current_user, tenant_id):
        raise HTTPException(status_code=403, detail="Sin permisos")
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo")

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = False
    user.updated_by_id = current_user.id
    user.updated_by_name = current_user.username
    await db.commit()
    return {"message": f"Usuario '{user.username}' desactivado correctamente"}
