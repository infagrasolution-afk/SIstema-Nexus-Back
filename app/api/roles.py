from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from app.core.database import get_master_db
from app.api.deps import get_current_user, require_permissions
from app.domain.user import User
from app.domain.rbac import Role, Permission, RolePermission
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, PermissionResponse

router = APIRouter()

@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(get_current_user)
):
    """Get all available permissions in the system."""
    result = await db.execute(select(Permission))
    return result.scalars().all()

@router.get("/", response_model=List[RoleResponse])
async def get_roles(
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(require_permissions(["settings:read"]))
):
    """Get all roles for the current tenant."""
    result = await db.execute(
        select(Role)
        .where(Role.tenant_id == current_user.tenant_id)
    )
    roles = result.scalars().all()
    # Eager load permissions
    for role in roles:
        perms_result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
        role.permissions = perms_result.scalars().all()
    return roles

@router.post("/", response_model=RoleResponse)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(require_permissions(["settings:write"]))
):
    """Create a new role with permissions."""
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
        rp = RolePermission(
            role_id=db_role.id, 
            permission_id=perm_id,
            tenant_id=current_user.tenant_id
        )
        db.add(rp)
        
    await db.commit()
    await db.refresh(db_role)
    return db_role

@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_master_db),
    current_user: User = Depends(require_permissions(["settings:write"]))
):
    """Delete a role."""
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == current_user.tenant_id)
    )
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot delete a system role")
        
    await db.delete(role)
    await db.commit()
    return {"message": "Role deleted"}
