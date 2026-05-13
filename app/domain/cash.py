from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base
from app.domain.base import TimestampMixin, TenantMixin

class SessionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"

class CashRegister(Base, TimestampMixin, TenantMixin):
    __tablename__ = "cash_registers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False) # e.g., "Caja 1"
    computer_uid = Column(String, unique=True, index=True, nullable=True) # Unique ID for the physical computer
    is_active = Column(Integer, default=1)

class CashSession(Base, TimestampMixin, TenantMixin):
    __tablename__ = "cash_sessions"
    id = Column(Integer, primary_key=True, index=True)
    register_id = Column(Integer, ForeignKey('cash_registers.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    opening_time = Column(DateTime, default=datetime.utcnow)
    closing_time = Column(DateTime, nullable=True)
    
    starting_cash = Column(Float, default=0.0)
    expected_cash = Column(Float, default=0.0) # Sum of sales in cash
    actual_cash = Column(Float, nullable=True) # Entered by user at closing
    
    status = Column(String, default=SessionStatus.OPEN)
    
    register = relationship("CashRegister")
    user = relationship("app.domain.user.User")
    sales = relationship("Sale", back_populates="cash_session")

# We need to update Sale model to include session_id
