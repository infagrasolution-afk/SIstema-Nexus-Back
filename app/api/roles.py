from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from app.core.database import get_master_db
from app.api.deps import get_current_user
from app.domain.user import User
from app.domain.rbac import Role, Permission, RolePermission
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, PermissionResponse

router = APIRouter()


def _can_manage_roles(current_user: User) -> bool:
    """Superadmin global O cualquier usuario autenticado de un tenant puede gestionar roles de su empresa."""
    return current_user.is_superuser or (current_user.tenant_id is not None)


# ─────────────────────────────────────────────────────────────────────────────
# Permisos del sistema (catálogo global)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PERMISSIONS = [
    # ── Inventario ──────────────────────────────────────────────────────────
    ("inventory:read",   "Ver inventario, productos, almacenes y stock",     "inventory"),
    ("inventory:write",  "Crear/editar productos, almacenes, categorías",    "inventory"),
    ("inventory:charge", "Registrar cargos de inventario (entradas)",        "inventory"),
    ("inventory:discharge","Registrar descargos de inventario (salidas)",    "inventory"),
    ("inventory:adjust", "Hacer ajustes de inventario",                      "inventory"),
    ("inventory:transfer","Transferir stock entre almacenes",                "inventory"),
    ("inventory:dispatch","Gestionar notas de despacho",                     "inventory"),

    # ── Ventas ──────────────────────────────────────────────────────────────
    ("sales:read",       "Ver ventas, facturas, presupuestos",               "sales"),
    ("sales:write",      "Crear ventas y presupuestos",                      "sales"),
    ("sales:void",       "Anular ventas",                                    "sales"),
    ("sales:customers",  "Gestionar clientes",                               "sales"),

    # ── Compras ─────────────────────────────────────────────────────────────
    ("purchases:read",   "Ver órdenes de compra",                            "purchases"),
    ("purchases:write",  "Crear órdenes de compra",                          "purchases"),
    ("purchases:suppliers","Gestionar proveedores",                          "purchases"),

    # ── Tesorería ───────────────────────────────────────────────────────────
    ("treasury:read",    "Ver cuentas por cobrar y pagar",                   "treasury"),
    ("treasury:write",   "Registrar pagos y cobros",                        "treasury"),

    # ── Contabilidad ────────────────────────────────────────────────────────
    ("accounting:read",  "Ver plan de cuentas y asientos",                   "accounting"),
    ("accounting:write", "Crear asientos contables",                         "accounting"),

    # ── Caja ────────────────────────────────────────────────────────────────
    ("cash:read",        "Ver sesiones de caja",                             "cash"),
    ("cash:write",       "Abrir y cerrar sesiones de caja",                  "cash"),

    # ── Configuración ───────────────────────────────────────────────────────
    ("settings:read",    "Ver configuración de la empresa",                  "settings"),
    ("settings:write",   "Modificar configuración de la empresa",            "settings"),

    # ── Reportes ────────────────────────────────────────────────────────────
    ("reports:read",     "Ver reportes y bitácora de movimientos",           "reports"),
]


async def seed_permissions(db: AsyncSession):
    """Inserta los permisos del sistema si no existen (idempotente)."""
    for code, description, module in SYSTEM_PERMISSIONS:
        existing = await db.execute(select(Permission).where(Permission.code == code))
        if not existing.scalars().first():
            db.add(Permission(code=code, description=description, module=module))
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# GET /roles/permissions  — Catálogo de permisos agrupados por módulo
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna todos los permisos del sistema. Usado para construir formularios de roles."""
    await seed_permissions(db)
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    return result.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /roles/  — Listar roles del tenant
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[RoleResponse])
async def get_roles(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Lista los roles de la empresa actual."""
    result = await db.execute(
        select(Role).where(Role.tenant_id == current_user.tenant_id)
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
# POST /roles/  — Crear rol con permisos
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea un nuevo rol para la empresa con los permisos seleccionados.
    Ejemplo: Rol 'Vendedor' con permisos [sales:read, sales:write, inventory:read]
    """
    if not _can_manage_roles(current_user):
        raise HTTPException(status_code=403, detail="Sin permisos para crear roles")

    # Verificar nombre único en el tenant
    existing = await db.execute(
        select(Role).where(Role.name == role_in.name, Role.tenant_id == current_user.tenant_id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Ya existe un rol con el nombre '{role_in.name}'")

    db_role = Role(
        name=role_in.name,
        description=role_in.description,
        tenant_id=current_user.tenant_id,
        created_by_id=current_user.id,
        created_by_name=current_user.username
    )
    db.add(db_role)
    await db.flush()

    for perm_id in role_in.permission_ids:
        db.add(RolePermission(
            role_id=db_role.id,
            permission_id=perm_id,
            tenant_id=current_user.tenant_id
        ))

    await db.commit()
    await db.refresh(db_role)

    # Cargar permisos para la respuesta
    perms_result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == db_role.id)
    )
    db_role.permissions = perms_result.scalars().all()
    return db_role


# ─────────────────────────────────────────────────────────────────────────────
# PUT /roles/{role_id}  — Actualizar rol y sus permisos
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Actualiza el nombre, descripción y permisos de un rol."""
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == current_user.tenant_id)
    )
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if role.is_system_role:
        raise HTTPException(status_code=400, detail="No se puede modificar un rol del sistema")

    if role_in.name:
        role.name = role_in.name
    if role_in.description is not None:
        role.description = role_in.description

    # Reemplazar permisos si se envían
    if role_in.permission_ids is not None:
        await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        for perm_id in role_in.permission_ids:
            db.add(RolePermission(
                role_id=role.id,
                permission_id=perm_id,
                tenant_id=current_user.tenant_id
            ))

    await db.commit()
    await db.refresh(role)

    perms_result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    )
    role.permissions = perms_result.scalars().all()
    return role


# ─────────────────────────────────────────────────────────────────────────────
# POST /roles/seed-defaults  — Crea roles predeterminados para la empresa
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/seed-defaults")
async def seed_default_roles(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea los roles predeterminados para la empresa si no existen:
    - Administrador (todos los permisos)
    - Vendedor (ventas + inventario lectura)
    - Almacenista (inventario completo)
    - Contador (contabilidad + tesorería)
    - Cajero (caja + ventas)
    """
    await seed_permissions(db)

    # Cargar todos los permisos
    all_perms = (await db.execute(select(Permission))).scalars().all()
    perm_map = {p.code: p.id for p in all_perms}

    DEFAULT_ROLES = [
        {
            "name": "Administrador",
            "description": "Acceso completo a todos los módulos",
            "codes": [p[0] for p in SYSTEM_PERMISSIONS],
            "is_system_role": True,
        },
        {
            "name": "Vendedor",
            "description": "Puede crear ventas, ver inventario y gestionar clientes",
            "codes": [
                "sales:read", "sales:write", "sales:customers",
                "inventory:read", "cash:read", "cash:write",
            ],
        },
        {
            "name": "Almacenista",
            "description": "Gestión completa de inventario y almacenes",
            "codes": [
                "inventory:read", "inventory:write", "inventory:charge",
                "inventory:discharge", "inventory:adjust", "inventory:transfer",
                "inventory:dispatch",
            ],
        },
        {
            "name": "Contador",
            "description": "Acceso a contabilidad, tesorería y reportes",
            "codes": [
                "accounting:read", "accounting:write",
                "treasury:read", "treasury:write",
                "purchases:read", "sales:read", "reports:read",
            ],
        },
        {
            "name": "Cajero",
            "description": "Manejo de caja y ventas",
            "codes": [
                "cash:read", "cash:write",
                "sales:read", "sales:write",
                "inventory:read",
            ],
        },
    ]

    created = []
    for role_def in DEFAULT_ROLES:
        # No crear si ya existe
        exists = await db.execute(
            select(Role).where(
                Role.name == role_def["name"],
                Role.tenant_id == current_user.tenant_id
            )
        )
        if exists.scalars().first():
            continue

        new_role = Role(
            name=role_def["name"],
            description=role_def["description"],
            tenant_id=current_user.tenant_id,
            is_system_role=role_def.get("is_system_role", False),
            created_by_id=current_user.id,
            created_by_name=current_user.username,
        )
        db.add(new_role)
        await db.flush()

        for code in role_def["codes"]:
            pid = perm_map.get(code)
            if pid:
                db.add(RolePermission(
                    role_id=new_role.id,
                    permission_id=pid,
                    tenant_id=current_user.tenant_id
                ))
        created.append(role_def["name"])

    await db.commit()
    return {
        "message": f"Roles creados: {', '.join(created) if created else 'Ninguno (ya existían)'}",
        "created": created
    }


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /roles/{role_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Elimina un rol. No se pueden eliminar roles del sistema."""
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == current_user.tenant_id)
    )
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if role.is_system_role:
        raise HTTPException(status_code=400, detail="No se puede eliminar un rol del sistema")

    await db.delete(role)
    await db.commit()
    return {"message": f"Rol '{role.name}' eliminado correctamente"}
