from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from app.core.database import Base
from app.domain.base import TenantMixin


class SystemMovement(Base, TenantMixin):
    """
    Tabla universal que registra TODOS los movimientos del sistema:
    Cargos, Descargos, Ajustes, Ventas, Compras, Pagos, Asientos Contables, Despachos.
    
    ARQUITECTURA MULTI-TENANT: Todos los campos de producto/almacén son desnormalizados
    (sin FK) para evitar JOINs cross-schema en PostgreSQL. Los IDs son referencias
    informativas, no integridad referencial.
    """
    __tablename__ = "system_movements"

    id = Column(Integer, primary_key=True, index=True)

    # ── Auditoría ──────────────────────────────────────────────
    created_at   = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    user_id      = Column(Integer, nullable=True)   # referencia sin FK (evita cross-schema)
    user_name    = Column(String, nullable=True)

    # ── Clasificación ──────────────────────────────────────────
    module       = Column(String, nullable=False, index=True)
    # INVENTORY | SALES | PURCHASES | TREASURY | ACCOUNTING | CASH

    operation    = Column(String, nullable=False, index=True)
    # CHARGE | DISCHARGE | ADJUSTMENT | TRANSFER | DISPATCH |
    # SALE | PURCHASE | PAYMENT_AR | PAYMENT_AP | JOURNAL_ENTRY | CASH_OPEN | CASH_CLOSE

    # ── Referencia al registro original ───────────────────────
    reference_id   = Column(Integer, nullable=True)
    reference_type = Column(String, nullable=True)
    reference_code = Column(String, nullable=True)

    # ── Producto / Inventario (desnormalizado — SIN FK cross-schema) ─────────
    product_id     = Column(Integer, nullable=True)   # referencia informativa
    product_name   = Column(String, nullable=True)
    product_sku    = Column(String, nullable=True)
    warehouse_id   = Column(Integer, nullable=True)   # referencia informativa
    warehouse_name = Column(String, nullable=True)
    quantity       = Column(Float, nullable=True)
    unit           = Column(String, nullable=True)

    # ── Valores monetarios ────────────────────────────────────
    amount    = Column(Float, nullable=True)
    unit_cost = Column(Float, nullable=True)
    currency  = Column(String, default="VES")

    # ── Descripción ───────────────────────────────────────────
    description = Column(Text, nullable=False)
    notes       = Column(Text, nullable=True)
    status      = Column(String, nullable=True)
