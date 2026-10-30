from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timezone
from decimal import Decimal
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin, AuditMixin

def utc_now():
    return datetime.now(timezone.utc)

class SessionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class CashRegister(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "cash_registers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False) # e.g., "Caja 1 - Principal"
    computer_uid = Column(String(100), unique=True, index=True, nullable=True) # Unique ID for the physical computer/POS
    is_active = Column(Integer, default=1)

class CashSession(Base, TimestampMixin, TenantMixin, AuditMixin):
    __tablename__ = "cash_sessions"
    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey('cash_registers.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    opening_time = Column(DateTime, default=utc_now, nullable=False)
    closing_time = Column(DateTime, nullable=True)
    
    # Montos en USD
    starting_cash = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    expected_cash = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False) # Total esperado en efectivo USD
    actual_cash = Column(Numeric(18, 4), nullable=True) # Conteo físico en cierre USD
    difference = Column(Numeric(18, 4), nullable=True) # actual - expected USD
    
    # Montos en VES (Bimonetario venezolano)
    starting_cash_ves = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False)
    expected_cash_ves = Column(Numeric(18, 4), default=Decimal('0.0000'), nullable=False) # Total esperado en efectivo Bs.
    actual_cash_ves = Column(Numeric(18, 4), nullable=True) # Conteo físico en cierre Bs.
    difference_ves = Column(Numeric(18, 4), nullable=True) # actual - expected Bs.
    
    notes = Column(Text, nullable=True)
    status = Column(String(20), default=SessionStatus.OPEN.value, nullable=False)
    
    register = relationship("CashRegister")
    user = relationship("app.domain.user.User")
    sales = relationship("Sale", back_populates="cash_session")
