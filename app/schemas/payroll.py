from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

# ── Employee Schemas ──────────────────────────────────────────────────────────

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    national_id: str
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    hire_date: date
    department: str = "Operaciones"
    position: str = "Personal Operativo"
    payment_frequency: str = "QUINCENAL"
    base_salary_usd: Decimal = Decimal('0.0000')
    base_salary_ves: Decimal = Decimal('0.0000')
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    sso_eligible: bool = True
    rpe_eligible: bool = True
    faov_eligible: bool = True
    cestaticket_eligible: bool = True
    is_active: bool = True
    notes: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    national_id: Optional[str] = None
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    hire_date: Optional[date] = None
    department: Optional[str] = None
    position: Optional[str] = None
    payment_frequency: Optional[str] = None
    base_salary_usd: Optional[Decimal] = None
    base_salary_ves: Optional[Decimal] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    sso_eligible: Optional[bool] = None
    rpe_eligible: Optional[bool] = None
    faov_eligible: Optional[bool] = None
    cestaticket_eligible: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class EmployeeResponse(EmployeeBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ── Payroll Receipt Schemas ───────────────────────────────────────────────────

class PayrollReceiptResponse(BaseModel):
    id: int
    period_id: int
    employee_id: int
    base_salary_amount: Decimal
    cesta_ticket: Decimal
    bonuses: Decimal
    overtime: Decimal
    gross_total: Decimal
    sso_deduction: Decimal
    rpe_deduction: Decimal
    faov_deduction: Decimal
    other_deductions: Decimal
    total_deductions: Decimal
    net_payable: Decimal
    currency: str
    exchange_rate: Decimal
    employee: Optional[EmployeeResponse] = None
    model_config = ConfigDict(from_attributes=True)

# ── Payroll Period Schemas ────────────────────────────────────────────────────

class PayrollPeriodBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    payment_date: date
    exchange_rate: Decimal = Decimal('1.0000')
    notes: Optional[str] = None

class PayrollPeriodCreate(PayrollPeriodBase):
    pass

class PayrollPeriodResponse(PayrollPeriodBase):
    id: int
    status: str
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    created_at: Optional[datetime] = None
    receipts: List[PayrollReceiptResponse] = []
    model_config = ConfigDict(from_attributes=True)
