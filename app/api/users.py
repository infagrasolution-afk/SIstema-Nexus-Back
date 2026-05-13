from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_current_user, get_current_tenant, get_master_db
from app.core.security import get_password_hash
from app.domain.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        # For simple multi-tenancy, regular users can see colleagues? 
        # Usually only admins can manage users.
        pass
        
    result = await db.execute(select(User).where(User.tenant_id == tenant_id))
    return result.scalars().all()

@router.post("/", response_model=UserResponse)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # Check if exists
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User already exists")
        
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=user_in.is_active,
        is_superuser=user_in.is_superuser,
        tenant_id=tenant_id
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
