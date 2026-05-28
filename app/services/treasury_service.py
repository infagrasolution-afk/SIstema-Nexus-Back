from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.domain.treasury import AccountsReceivable, AccountsPayable, TreasuryPayment, DebtStatus
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
        # 1. Register Payment
        new_payment = TreasuryPayment(
            **payment_in.model_dump(),
            tenant_id=tenant_id
        )
        db.add(new_payment)

        # 2. Update Debt Balance
        counterpart_name = "Desconocido"
        operation = "PAYMENT_AR"
        if payment_in.ar_id:
            result = await db.execute(
                select(AccountsReceivable).where(AccountsReceivable.id == payment_in.ar_id)
            )
            debt = result.scalars().first()
            operation = "PAYMENT_AR"
        else:
            result = await db.execute(
                select(AccountsPayable).where(AccountsPayable.id == payment_in.ap_id)
            )
            debt = result.scalars().first()
            operation = "PAYMENT_AP"

        if debt:
            debt.remaining_amount -= payment_in.amount
            if debt.remaining_amount <= 0:
                debt.status = DebtStatus.PAID
                debt.remaining_amount = 0
            else:
                debt.status = DebtStatus.PARTIAL

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
