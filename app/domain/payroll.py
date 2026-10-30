from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Boolean, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from decimal import Decimal
import enum
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

def utc_now():
    return datetime.now(timezone.utc)

class PayrollPeriodStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CALCULATED = "CALCULATED"
    CLOSED = "CLOSED"

class Employee(Base, TimestampMixin, TenantMixin, AuditMixin):
    """
    Ficha de Empleado conforme a la Ley Orgánica del Trabajo (LOTTT Venezuela).
    """
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    national_id = Column(String(30), nullable=False, index=True) # Cédula de Identidad (V-12345678 / E-87654321)
    tax_id = Column(String(30), nullable=True) # R.I.F. Personal
    email = Column(String(120), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)

    # Datos Laborales
    hire_date = Column(Date, nullable=False)
    department = Column(String(100), nullable=False, default="Operaciones")
    position = Column(String(100), nullable=False, default="Personal Operativo")
    payment_frequency = Column(String(20), nullable=False, default="QUINCENAL") # QUINCENAL | MENSUAL

    # Salarios y Divisas (Bimonetario)
    base_salary_usd = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    base_salary_ves = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)

    # Datos Bancarios para Nómina
    bank_name = Column(String(100), nullable=True) # e.g., Banco de Venezuela, Banesco
    bank_account = Column(String(50), nullable=True) # 20 dígitos

    # Beneficios y Ley
    sso_eligible = Column(Boolean, default=True) # Seguro Social Obligatorio (4%)
    rpe_eligible = Column(Boolean, default=True) # Régimen Prestacional de Empleo / Paro Forzoso (0.5%)
    faov_eligible = Column(Boolean, default=True) # FAOV / Banavih (1%)
    cestaticket_eligible = Column(Boolean, default=True) # Cestaticket Socialista de Alimentación

    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    receipts = relationship("PayrollReceipt", back_populates="employee", cascade="all, delete-orphan")


class PayrollPeriod(Base, TimestampMixin, TenantMixin, AuditMixin):
    """
    Período de Nómina (e.g., 1ra Quincena Octubre 2026).
    """
    __tablename__ = "payroll_periods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False) # "1ra Quincena Octubre 2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=False)
    exchange_rate = Column(Numeric(18, 4), default=Decimal('1.0000'), nullable=False)
    status = Column(String(20), default=PayrollPeriodStatus.DRAFT.value, nullable=False)

    total_gross = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    total_deductions = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    total_net = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    notes = Column(Text, nullable=True)

    receipts = relationship("PayrollReceipt", back_populates="period", cascade="all, delete-orphan")


class PayrollReceipt(Base, TimestampMixin, TenantMixin, AuditMixin):
    """
    Recibo de Pago de Nómina Individual por Empleado.
    """
    __tablename__ = "payroll_receipts"

    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey('payroll_periods.id', ondelete='CASCADE'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)

    # Asignaciones (Ingresos)
    base_salary_amount = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    cesta_ticket = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    bonuses = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    overtime = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    gross_total = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)

    # Deducciones de Ley Venezolana (LOTTT / IVSS / BANAVIH)
    sso_deduction = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False) # 4% IVSS
    rpe_deduction = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False) # 0.5% Empleo
    faov_deduction = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False) # 1% Vivienda
    other_deductions = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    total_deductions = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)

    # Monto Neto
    net_payable = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    currency = Column(String(10), default="USD", nullable=False)
    exchange_rate = Column(Numeric(18, 4), default=Decimal('1.0000'), nullable=False)

    employee = relationship("Employee", back_populates="receipts")
    period = relationship("PayrollPeriod", back_populates="receipts")
