from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.api import deps
from app.api.deps import require_module
from app.services.accounting_service import AccountingService
from app.schemas.accounting import Account, AccountCreate, JournalEntry, JournalEntryCreate
from app.domain.user import User

router = APIRouter()

@router.get("/accounts", response_model=List[Account])
async def get_accounts(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting")),
):
    return await AccountingService.get_accounts(db, current_user.tenant_id)

@router.post("/accounts", response_model=Account)
async def create_account(
    account_in: AccountCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting")),
):
    return await AccountingService.create_account(db, account_in, current_user.tenant_id)

@router.get("/journal-entries", response_model=List[JournalEntry])
async def get_journal_entries(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting")),
):
    return await AccountingService.get_journal_entries(db, current_user.tenant_id)

@router.post("/account-session/{session_id}")
async def account_session(
    session_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return await AccountingService.account_session_sales(db, session_id, current_user.tenant_id)

@router.post("/account-purchases")
async def account_purchases(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    return await AccountingService.account_pending_purchases(db, current_user.tenant_id)

@router.post("/journal-entries", response_model=JournalEntry)
async def create_journal_entry(
    entry_in: JournalEntryCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    try:
        return await AccountingService.create_journal_entry(db, entry_in, current_user.tenant_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
