from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from decimal import Decimal
from app.domain.treasury import AccountsReceivable, AccountsPayable, TreasuryPayment, DebtStatus, BankAccount
from app.schemas.treasury import TreasuryPaymentCreate
from app.services.accounting_service import AccountingService
from app.services.movement_logger import MovementLogger

class TreasuryService:
    @staticmethod
    async def create_ar(db: AsyncSession, sale_id: int, customer_id: int, total: float, tenant_id: int):
        ar = AccountsReceivable(
            sale_id=sale_id,
            customer_id=customer_id,
            total_amount=total,
            remaining_amount=total,
            due_date=datetime.now() + timedelta(days=30), # Default 30 days
            status=DebtStatus.OPEN,
            tenant_id=tenant_id
        )
        db.add(ar)
        await db.flush()
        return ar

    @staticmethod
    async def create_ap(db: AsyncSession, purchase_id: int, supplier_id: int, total: float, tenant_id: int):
        ap = AccountsPayable(
            purchase_id=purchase_id,
            supplier_id=supplier_id,
            total_amount=total,
            remaining_amount=total,
            due_date=datetime.now() + timedelta(days=30),
            status=DebtStatus.OPEN,
            tenant_id=tenant_id
        )
        db.add(ap)
        await db.flush()
        return ap

    @staticmethod
    async def process_payment(
        db: AsyncSession,
        payment_in: TreasuryPaymentCreate,
        tenant_id: int,
        user_id: int = None,
        user_name: str = None
    ):
        amount = Decimal(str(payment_in.amount or 0))
        if amount <= Decimal("0"):
            raise HTTPException(status_code=400, detail="El monto del pago debe ser mayor a cero.")
        if not payment_in.ar_id and not payment_in.ap_id:
            raise HTTPException(status_code=400, detail="Debe especificar una cuenta por cobrar (ar_id) o por pagar (ap_id).")

        # 1. Load & Validate Debt Balance
        counterpart_name = "Desconocido"
        operation = "PAYMENT_AR"
        if payment_in.ar_id:
            result = await db.execute(
                select(AccountsReceivable)
                .where(AccountsReceivable.id == payment_in.ar_id, AccountsReceivable.tenant_id == tenant_id)
                .options(selectinload(AccountsReceivable.customer))
            )
            debt = result.scalars().first()
            operation = "PAYMENT_AR"
            if debt and debt.customer:
                counterpart_name = debt.customer.name
        else:
            result = await db.execute(
                select(AccountsPayable)
                .where(AccountsPayable.id == payment_in.ap_id, AccountsPayable.tenant_id == tenant_id)
                .options(selectinload(AccountsPayable.supplier))
            )
            debt = result.scalars().first()
            operation = "PAYMENT_AP"
            if debt and debt.supplier:
                counterpart_name = debt.supplier.name

        if not debt:
            raise HTTPException(status_code=404, detail="Documento por cobrar/pagar no encontrado.")

        remaining = Decimal(str(debt.remaining_amount))
        if debt.status == DebtStatus.PAID or remaining <= Decimal("0"):
            raise HTTPException(status_code=400, detail="Este documento ya se encuentra totalmente pagado.")
        if amount > remaining + Decimal("0.01"):
            raise HTTPException(
                status_code=400,
                detail=f"El monto ({amount:.2f}) excede el saldo pendiente ({remaining:.2f})."
            )

        # 2. Register Payment
        new_payment = TreasuryPayment(
            **payment_in.model_dump(),
            tenant_id=tenant_id
        )
        db.add(new_payment)

        # 3. Update Debt Balance
        new_remaining = remaining - amount
        if new_remaining <= Decimal("0.005"):
            debt.status = DebtStatus.PAID
            debt.remaining_amount = Decimal("0.0000")
        else:
            debt.remaining_amount = new_remaining
            debt.status = DebtStatus.PARTIAL

        # 4. Update Bank Account Balance if linked
        if payment_in.bank_account_id:
            bank_res = await db.execute(
                select(BankAccount).where(
                    BankAccount.id == payment_in.bank_account_id,
                    BankAccount.tenant_id == tenant_id
                )
            )
            bank_acc = bank_res.scalars().first()
            if bank_acc:
                bank_delta = amount
                pay_curr = (payment_in.currency or "USD").upper()
                bank_curr = (bank_acc.currency or "USD").upper()
                rate = Decimal(str(payment_in.exchange_rate or 1))
                if pay_curr != bank_curr and rate > Decimal("0"):
                    # Debts are tracked in USD base: if bank is VES and payment is USD, multiply; if bank is USD and payment is VES, divide
                    if bank_curr == "VES" and pay_curr == "USD":
                        bank_delta = amount * rate
                    elif bank_curr == "USD" and pay_curr == "VES":
                        bank_delta = amount / rate
                current_bal = Decimal(str(bank_acc.current_balance or 0))
                if operation == "PAYMENT_AR":
                    bank_acc.current_balance = current_bal + bank_delta
                else:
                    bank_acc.current_balance = current_bal - bank_delta

        await db.flush()
        await AccountingService.account_treasury_payment(db, new_payment.id, tenant_id)

        # 3. Log payment
        await MovementLogger.log_payment(
            db=db,
            tenant_id=tenant_id,
            payment_id=new_payment.id,
            operation=operation,
            counterpart_name=counterpart_name,
            amount=payment_in.amount,
            payment_method=payment_in.payment_method,
            user_id=user_id,
            user_name=user_name,
        )

        await db.commit()
        return new_payment
