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

@router.post("/accounts/import")
async def import_accounts(
    accounts_in: List[AccountCreate],
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting")),
):
    try:
        return await AccountingService.bulk_create_accounts(db, accounts_in, current_user.tenant_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

@router.get("/pnl")
async def get_pnl_report(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting")),
):
    return await AccountingService.get_pnl(db, current_user.tenant_id)

# --- Bank Reconciliation ---
from app.domain.accounting import BankStatement, BankStatementLine, JournalEntryDetail
from app.schemas.accounting import BankStatementCreate, BankStatementResponse, BankStatementLineCreate, BankStatementLineResponse

@router.get("/bank-statements", response_model=List[BankStatementResponse])
async def get_bank_statements(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting"))
):
    result = await db.execute(
        select(BankStatement)
        .where(BankStatement.tenant_id == current_user.tenant_id)
        .options(selectinload(BankStatement.lines))
        .order_by(BankStatement.year.desc(), BankStatement.month.desc())
    )
    return result.scalars().all()

@router.post("/bank-statements", response_model=BankStatementResponse)
async def create_bank_statement(
    stmt_in: BankStatementCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting"))
):
    stmt = BankStatement(**stmt_in.model_dump(), tenant_id=current_user.tenant_id)
    db.add(stmt)
    await db.commit()
    await db.refresh(stmt)
    
    # Load relationships
    res = await db.execute(
        select(BankStatement).where(BankStatement.id == stmt.id).options(selectinload(BankStatement.lines))
    )
    return res.scalars().first()

@router.post("/bank-statements/{statement_id}/lines")
async def add_bank_lines(
    statement_id: int,
    lines_in: List[BankStatementLineCreate],
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting"))
):
    # Verify statement
    result = await db.execute(select(BankStatement).where(BankStatement.id == statement_id, BankStatement.tenant_id == current_user.tenant_id))
    stmt = result.scalars().first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Estado de cuenta no encontrado")
        
    for l in lines_in:
        db.add(BankStatementLine(**l.model_dump(), statement_id=statement_id, tenant_id=current_user.tenant_id))
        
    await db.commit()
    return {"message": f"{len(lines_in)} líneas agregadas"}

@router.post("/bank-statements/{statement_id}/auto-reconcile")
async def auto_reconcile_bank_statement(
    statement_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    _: bool = Depends(require_module("accounting"))
):
    """
    Attempts to automatically match bank statement lines with JournalEntryDetails for the same account.
    Match criteria: Exact amount.
    """
    # 1. Fetch statement & lines
    result = await db.execute(
        select(BankStatement).where(BankStatement.id == statement_id, BankStatement.tenant_id == current_user.tenant_id)
        .options(selectinload(BankStatement.lines))
    )
    stmt = result.scalars().first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Estado de cuenta no encontrado")
        
    # 2. Fetch unreconciled journal entry details for this bank account
    # We want debit for positive amount (in), credit for negative amount (out)
    je_result = await db.execute(
        select(JournalEntryDetail)
        .where(
            JournalEntryDetail.account_id == stmt.account_id,
            JournalEntryDetail.tenant_id == current_user.tenant_id
        )
    )
    je_details = je_result.scalars().all()
    
    # Simple auto-match
    matched = 0
    used_je_ids = set()
    
    # We also find already reconciled line's JE IDs to not reuse them
    for l in stmt.lines:
        if l.linked_journal_detail_id:
            used_je_ids.add(l.linked_journal_detail_id)
            
    for line in stmt.lines:
        if line.is_reconciled:
            continue
            
        for je in je_details:
            if je.id in used_je_ids:
                continue
            
            # Amount logic: if line.amount is positive (deposit to bank), it should be a debit in the asset account
            if line.amount > 0 and abs(je.debit - line.amount) < 0.01:
                line.is_reconciled = True
                line.linked_journal_detail_id = je.id
                used_je_ids.add(je.id)
                matched += 1
                break
                
            # If line.amount is negative (withdrawal), it should be a credit in the asset account
            if line.amount < 0 and abs(je.credit - abs(line.amount)) < 0.01:
                line.is_reconciled = True
                line.linked_journal_detail_id = je.id
                used_je_ids.add(je.id)
                matched += 1
                break
                
    await db.commit()
    return {"message": f"Auto-conciliación completada. {matched} líneas emparejadas automáticamente."}
