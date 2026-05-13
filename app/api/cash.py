from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.api import deps
from app.services.cash_service import CashService
from app.schemas.cash import CashSession, CashSessionCreate, CashSessionClose, CashRegister
from app.domain.user import User

router = APIRouter()

@router.get("/session/current", response_model=Optional[CashSession])
async def get_current_session(
    computer_uid: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return await CashService.get_current_session(db, computer_uid, current_user.tenant_id)

@router.post("/session/open", response_model=CashSession)
async def open_session(
    session_in: CashSessionCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return await CashService.open_session(db, session_in, current_user.id, current_user.tenant_id)

@router.post("/session/{session_id}/close", response_model=CashSession)
async def close_session(
    session_id: int,
    close_in: CashSessionClose,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return await CashService.close_session(db, session_id, close_in, current_user.tenant_id)

@router.get("/registers", response_model=List[CashRegister])
async def get_registers(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    from app.domain.cash import CashRegister as DBCashRegister
    from sqlalchemy import select
    stmt = select(DBCashRegister).where(DBCashRegister.tenant_id == current_user.tenant_id)
    result = await db.execute(stmt)
    return result.scalars().all()
