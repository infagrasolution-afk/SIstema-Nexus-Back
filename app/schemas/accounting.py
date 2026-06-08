from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

class AccountBase(BaseModel):
    code: str
    name: str
    type: str

class AccountCreate(AccountBase):
    pass

class Account(AccountBase):
    id: int
    balance: float
    is_active: bool
    tenant_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class JournalEntryDetailBase(BaseModel):
    account_id: int
    debit: float = 0.0
    credit: float = 0.0

class JournalEntryDetailCreate(JournalEntryDetailBase):
    pass

class JournalEntryDetail(JournalEntryDetailBase):
    id: int
    journal_entry_id: int

    model_config = ConfigDict(from_attributes=True)

class JournalEntryBase(BaseModel):
    reference: Optional[str] = None
    description: str

class JournalEntryCreate(JournalEntryBase):
    details: List[JournalEntryDetailCreate]

class JournalEntry(JournalEntryBase):
    id: int
    date: datetime
    tenant_id: int
    details: List[JournalEntryDetail]

    model_config = ConfigDict(from_attributes=True)

class BankStatementLineBase(BaseModel):
    date: datetime
    description: str
    reference: Optional[str] = None
    amount: float

class BankStatementLineCreate(BankStatementLineBase):
    pass

class BankStatementLineResponse(BankStatementLineBase):
    id: int
    statement_id: int
    is_reconciled: bool
    linked_journal_detail_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

class BankStatementBase(BaseModel):
    account_id: int
    month: int
    year: int

class BankStatementCreate(BankStatementBase):
    pass

class BankStatementResponse(BankStatementBase):
    id: int
    status: str
    tenant_id: int
    lines: List[BankStatementLineResponse] = []
    model_config = ConfigDict(from_attributes=True)
