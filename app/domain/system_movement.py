from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from datetime import datetime, timezone
from decimal import Decimal
from app.core.database import Base
from app.domain.base import TenantMixin

def utc_now():
    return datetime.now(timezone.utc)


class SystemMovement(Base, TenantMixin):
    """
    Tabla universal que registra TODOS los movimientos del sistema:
    Cargos, Descargos, Ajustes, Ventas, Compras, Pagos, Asientos Contables, Despachos, Notas de Crédito/Débito.
    
    ARQUITECTURA MULTI-TENANT: Todos los campos de producto/almacén son desnormalizados
    (sin FK) para evitar JOINs cross-schema en PostgreSQL. Los IDs son referencias
    informativas, no integridad referencial.
    """
    __tablename__ = "system_movements"

    id = Column(Integer, primary_key=True, index=True)

    # ── Auditoría ──────────────────────────────────────────────
    created_at   = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    user_id      = Column(Integer, nullable=True)   # referencia sin FK (evita cross-schema)
    user_name    = Column(String(150), nullable=True)

    # ── Clasificación ──────────────────────────────────────────
    module       = Column(String(50), nullable=False, index=True)
    # INVENTORY | SALES | PURCHASES | TREASURY | ACCOUNTING | CASH

    operation    = Column(String(50), nullable=False, index=True)
    # CHARGE | DISCHARGE | ADJUSTMENT | TRANSFER | DISPATCH |
    # SALE | PURCHASE | CREDIT_NOTE | DEBIT_NOTE | PAYMENT_AR | PAYMENT_AP | JOURNAL_ENTRY | CASH_OPEN | CASH_CLOSE

    # ── Referencia al registro original ───────────────────────
    reference_id   = Column(Integer, nullable=True)
    reference_type = Column(String(50), nullable=True)
    reference_code = Column(String(100), nullable=True)

    # ── Producto / Inventario (desnormalizado — SIN FK cross-schema) ─────────
    product_id     = Column(Integer, nullable=True)   # referencia informativa
    product_name   = Column(String(255), nullable=True)
    product_sku    = Column(String(100), nullable=True)
    warehouse_id   = Column(Integer, nullable=True)   # referencia informativa
    warehouse_name = Column(String(150), nullable=True)
    quantity       = Column(Numeric(18, 4), nullable=True)
    unit           = Column(String(50), nullable=True)

    # ── Valores monetarios ────────────────────────────────────
    amount        = Column(Numeric(18, 4), nullable=True)
    unit_cost     = Column(Numeric(18, 4), nullable=True)
    currency      = Column(String(10), default="USD", nullable=False)
    exchange_rate = Column(Numeric(18, 4), default=Decimal('1.0000'), nullable=False)

    # ── Descripción ───────────────────────────────────────────
    description = Column(Text, nullable=False)
    notes       = Column(Text, nullable=True)
    status      = Column(String(50), nullable=True)
