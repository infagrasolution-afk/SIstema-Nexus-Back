"""
MovementLogger — Servicio central para registrar todos los movimientos del sistema.
Se llama desde WMSService, SalesService, PurchaseService, TreasuryService, etc.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.system_movement import SystemMovement


class MovementLogger:

    # ── INVENTARIO ────────────────────────────────────────────────────────────

    @staticmethod
    async def log_stock_movement(
        db: AsyncSession,
        *,
        tenant_id: int,
        operation: str,            # CHARGE | DISCHARGE | ADJUSTMENT | TRANSFER | DISPATCH
        product_id: int,
        product_name: str,
        product_sku: str,
        warehouse_id: int,
        warehouse_name: str,
        quantity: float,
        unit: str = "unidades",
        reference_id: int = None,
        reference_code: str = None,
        unit_cost: float = None,
        currency: str = "VES",
        user_id: int = None,
        user_name: str = None,
        notes: str = None,
        description: str = None,
        status: str = "COMPLETED",
    ):
        labels = {
            "CHARGE":     "Cargo de inventario",
            "DISCHARGE":  "Descargo de inventario",
            "ADJUSTMENT": "Ajuste de inventario",
            "TRANSFER":   "Transferencia entre almacenes",
            "DISPATCH":   "Nota de despacho",
        }
        auto_desc = description or (
            f"{labels.get(operation, operation)}: {quantity} {unit} de «{product_name}» "
            f"en almacén «{warehouse_name}»"
            + (f" — Ref: {reference_code}" if reference_code else "")
        )
        entry = SystemMovement(
            tenant_id=tenant_id,
            module="INVENTORY",
            operation=operation,
            reference_id=reference_id,
            reference_type="StockMovement",
            reference_code=reference_code,
            product_id=product_id,
            product_name=product_name,
            product_sku=product_sku,
            warehouse_id=warehouse_id,
            warehouse_name=warehouse_name,
            quantity=quantity,
            unit=unit,
            unit_cost=unit_cost,
            currency=currency,
            user_id=user_id,
            user_name=user_name,
            description=auto_desc,
            notes=notes,
            status=status,
            created_at=datetime.utcnow(),
        )
        db.add(entry)

    # ── VENTAS ────────────────────────────────────────────────────────────────

    @staticmethod
    async def log_sale(
        db: AsyncSession,
        *,
        tenant_id: int,
        sale_id: int,
        customer_name: str,
        total: float,
        currency: str = "VES",
        payment_method: str = None,
        user_id: int = None,
        user_name: str = None,
        status: str = "COMPLETED",
        notes: str = None,
    ):
        entry = SystemMovement(
            tenant_id=tenant_id,
            module="SALES",
            operation="SALE",
            reference_id=sale_id,
            reference_type="Sale",
            reference_code=f"VENTA-{sale_id:06d}",
            amount=total,
            currency=currency,
            user_id=user_id,
            user_name=user_name,
            description=(
                f"Venta #{sale_id:06d} a «{customer_name}» por {currency} {total:,.2f}"
                + (f" — {payment_method}" if payment_method else "")
            ),
            notes=notes,
            status=status,
            created_at=datetime.utcnow(),
        )
        db.add(entry)

    # ── COMPRAS ───────────────────────────────────────────────────────────────

    @staticmethod
    async def log_purchase(
        db: AsyncSession,
        *,
        tenant_id: int,
        purchase_id: int,
        supplier_name: str,
        total: float,
        currency: str = "VES",
        payment_method: str = None,
        reference: str = None,
        user_id: int = None,
        user_name: str = None,
        status: str = "COMPLETED",
        notes: str = None,
    ):
        entry = SystemMovement(
            tenant_id=tenant_id,
            module="PURCHASES",
            operation="PURCHASE",
            reference_id=purchase_id,
            reference_type="Purchase",
            reference_code=reference or f"COMPRA-{purchase_id:06d}",
            amount=total,
            currency=currency,
            user_id=user_id,
            user_name=user_name,
            description=(
                f"Compra #{purchase_id:06d} a proveedor «{supplier_name}» por {currency} {total:,.2f}"
                + (f" — {payment_method}" if payment_method else "")
            ),
            notes=notes,
            status=status,
            created_at=datetime.utcnow(),
        )
        db.add(entry)

    # ── TESORERÍA ─────────────────────────────────────────────────────────────

    @staticmethod
    async def log_payment(
        db: AsyncSession,
        *,
        tenant_id: int,
        payment_id: int,
        operation: str,   # PAYMENT_AR | PAYMENT_AP
        counterpart_name: str,
        amount: float,
        currency: str = "VES",
        payment_method: str = None,
        user_id: int = None,
        user_name: str = None,
        notes: str = None,
    ):
        label = "Cobro a cliente" if operation == "PAYMENT_AR" else "Pago a proveedor"
        entry = SystemMovement(
            tenant_id=tenant_id,
            module="TREASURY",
            operation=operation,
            reference_id=payment_id,
            reference_type="TreasuryPayment",
            reference_code=f"PAGO-{payment_id:06d}",
            amount=amount,
            currency=currency,
            user_id=user_id,
            user_name=user_name,
            description=(
                f"{label}: «{counterpart_name}» — {currency} {amount:,.2f}"
                + (f" vía {payment_method}" if payment_method else "")
            ),
            notes=notes,
            status="COMPLETED",
            created_at=datetime.utcnow(),
        )
        db.add(entry)

    # ── CONTABILIDAD ──────────────────────────────────────────────────────────

    @staticmethod
    async def log_journal_entry(
        db: AsyncSession,
        *,
        tenant_id: int,
        entry_id: int,
        description: str,
        reference: str = None,
        total_debit: float = None,
        user_id: int = None,
        user_name: str = None,
    ):
        entry = SystemMovement(
            tenant_id=tenant_id,
            module="ACCOUNTING",
            operation="JOURNAL_ENTRY",
            reference_id=entry_id,
            reference_type="JournalEntry",
            reference_code=reference,
            amount=total_debit,
            user_id=user_id,
            user_name=user_name,
            description=f"Asiento contable #{entry_id}: {description}"
            + (f" — Ref: {reference}" if reference else ""),
            status="COMPLETED",
            created_at=datetime.utcnow(),
        )
        db.add(entry)

    # ── CAJA ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def log_cash_session(
        db: AsyncSession,
        *,
        tenant_id: int,
        session_id: int,
        operation: str,     # CASH_OPEN | CASH_CLOSE
        amount: float,
        user_id: int = None,
        user_name: str = None,
        notes: str = None,
    ):
        label = "Apertura de caja" if operation == "CASH_OPEN" else "Cierre de caja"
        entry = SystemMovement(
            tenant_id=tenant_id,
            module="CASH",
            operation=operation,
            reference_id=session_id,
            reference_type="CashSession",
            reference_code=f"CAJA-{session_id:06d}",
            amount=amount,
            user_id=user_id,
            user_name=user_name,
            description=f"{label} #{session_id} — Monto: {amount:,.2f}",
            notes=notes,
            status="COMPLETED",
            created_at=datetime.utcnow(),
        )
        db.add(entry)
