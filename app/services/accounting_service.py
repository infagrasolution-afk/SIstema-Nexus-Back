from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from datetime import datetime
from app.domain.accounting import Account, JournalEntry, JournalEntryDetail, AccountType
from app.domain.sales import Sale
from app.domain.purchases import Purchase, PurchaseStatus
from app.schemas.accounting import AccountCreate, JournalEntryCreate
from fastapi import HTTPException, status

class AccountingService:
    @staticmethod
    async def init_default_accounts(db: AsyncSession, tenant_id: str):
        stmt = select(Account).where(Account.tenant_id == tenant_id)
        result = await db.execute(stmt)
        if result.scalars().first():
            return # Already initialized
        
        defaults = [
            # Cuentas base obligatorias para el funcionamiento
            Account(code="1000", name="Caja / Banco Principal", type=AccountType.ASSET, tenant_id=tenant_id),
            Account(code="1100", name="Cuentas por Cobrar Comerciales", type=AccountType.ASSET, tenant_id=tenant_id),
            Account(code="2000", name="Cuentas por Pagar Proveedores", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="3000", name="Capital Social", type=AccountType.EQUITY, tenant_id=tenant_id),
            Account(code="4000", name="Ingresos por Ventas", type=AccountType.REVENUE, tenant_id=tenant_id),
            Account(code="5000", name="Gastos / Compras", type=AccountType.EXPENSE, tenant_id=tenant_id),
            
            # Cuentas específicas para cumplimiento de Leyes Venezolanas (VEN-NIF e Impuestos SENIAT)
            Account(code="1140", name="Crédito Fiscal IVA (Compras 16%)", type=AccountType.ASSET, tenant_id=tenant_id),
            Account(code="1150", name="Anticipos de Impuestos (Retenciones IVA/ISLR)", type=AccountType.ASSET, tenant_id=tenant_id),
            Account(code="2120", name="Débito Fiscal IVA (Ventas 16%)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="2130", name="Retenciones de IVA por Enterar (SENIAT)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="2140", name="Retenciones de ISLR por Enterar (SENIAT)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="2160", name="IGTF por Pagar (3%)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="4110", name="Ganancia Cambiaria (Diferencial Cambiario BCV)", type=AccountType.REVENUE, tenant_id=tenant_id),
            Account(code="5202", name="Gastos de IGTF Pagados (3%)", type=AccountType.EXPENSE, tenant_id=tenant_id),
            Account(code="5204", name="Pérdida Cambiaria (Diferencial Cambiario BCV)", type=AccountType.EXPENSE, tenant_id=tenant_id),
        ]
        db.add_all(defaults)
        await db.commit()

    @staticmethod
    async def get_accounts(db: AsyncSession, tenant_id: str):
        await AccountingService.init_default_accounts(db, tenant_id)
        stmt = select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_account(db: AsyncSession, account_in: AccountCreate, tenant_id: str):
        account = Account(**account_in.model_dump(), tenant_id=tenant_id)
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def bulk_create_accounts(db: AsyncSession, accounts_in: list[AccountCreate], tenant_id: str):
        # 1. Fetch existing accounts to check for duplicates by code
        stmt = select(Account.code).where(Account.tenant_id == tenant_id)
        result = await db.execute(stmt)
        existing_codes = set(result.scalars().all())
        
        imported_count = 0
        new_accounts = []
        
        for acc_in in accounts_in:
            if acc_in.code not in existing_codes:
                new_account = Account(**acc_in.model_dump(), tenant_id=tenant_id)
                new_accounts.append(new_account)
                existing_codes.add(acc_in.code)
                imported_count += 1
                
        if new_accounts:
            db.add_all(new_accounts)
            await db.commit()
            
        return {"imported": imported_count}

    @staticmethod
    async def create_journal_entry(db: AsyncSession, entry_in: JournalEntryCreate, tenant_id: str):
        # Validate that debits == credits
        total_debit = sum(d.debit for d in entry_in.details)
        total_credit = sum(d.credit for d in entry_in.details)
        
        if abs(total_debit - total_credit) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asiento contable desbalanceado. Débito total: ${total_debit:.2f}, Crédito total: ${total_credit:.2f}. Deben ser iguales."
            )
            
        je = JournalEntry(
            reference=entry_in.reference,
            description=entry_in.description,
            tenant_id=tenant_id
        )
        db.add(je)
        await db.flush()
        
        for d in entry_in.details:
            detail = JournalEntryDetail(
                journal_entry_id=je.id,
                account_id=d.account_id,
                debit=d.debit,
                credit=d.credit,
                tenant_id=tenant_id
            )
            db.add(detail)
            
            # Update account balance
            result = await db.execute(select(Account).where(Account.id == d.account_id))
            account = result.scalars().first()
            if account:
                if account.type in [AccountType.ASSET, AccountType.EXPENSE]:
                    account.balance += (d.debit - d.credit)
                else:
                    account.balance += (d.credit - d.debit)
                    
        await db.commit()
        return je

    @staticmethod
    async def get_journal_entries(db: AsyncSession, tenant_id: str):
        from sqlalchemy.orm import selectinload
        stmt = select(JournalEntry).where(JournalEntry.tenant_id == tenant_id).options(
            selectinload(JournalEntry.details).selectinload(JournalEntryDetail.account)
        ).order_by(JournalEntry.date.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def account_session_sales(db: AsyncSession, session_id: int, tenant_id: str):
        await AccountingService.init_default_accounts(db, tenant_id)
        
        # Get un-accounted sales for this session
        stmt = select(Sale).where(
            Sale.cash_session_id == session_id,
            Sale.is_accounted == False,
            Sale.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        sales = result.scalars().all()
        
        if not sales:
            return {"message": "No hay ventas nuevas para contabilizar en esta sesión."}
            
        total_cash = sum(s.total for s in sales if s.payment_method != "credit")
        total_credit = sum(s.total for s in sales if s.payment_method == "credit")
        total_revenue = total_cash + total_credit
        
        # Get accounts
        acc_stmt = select(Account).where(Account.tenant_id == tenant_id)
        accounts = (await db.execute(acc_stmt)).scalars().all()
        caja = next((a for a in accounts if a.code == "1000"), None)
        cxc = next((a for a in accounts if a.code == "1100"), None)
        ingresos = next((a for a in accounts if a.code == "4000"), None)
        
        if not caja or not ingresos or not cxc:
            raise HTTPException(status_code=500, detail="Cuentas contables por defecto no encontradas (Caja, CxC o Ingresos)")
            
        # Create Journal Entry
        je = JournalEntry(
            reference=f"Cierre Sesión {session_id}",
            description=f"Contabilización de {len(sales)} ventas ({len(sales)-len([s for s in sales if s.payment_method=='credit'])} contado, {len([s for s in sales if s.payment_method=='credit'])} crédito)",
            tenant_id=tenant_id
        )
        db.add(je)
        await db.flush()
        
        # Details
        if total_cash > 0:
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=caja.id, debit=total_cash, tenant_id=tenant_id))
            caja.balance += total_cash
            
        if total_credit > 0:
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=cxc.id, debit=total_credit, tenant_id=tenant_id))
            cxc.balance += total_credit
            
        db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=ingresos.id, credit=total_revenue, tenant_id=tenant_id))
        ingresos.balance += total_revenue
        
        # Mark sales as accounted
        for s in sales:
            s.is_accounted = True
            
        await db.commit()
        return {"message": f"Contabilizadas {len(sales)} ventas por un total de ${total_revenue}"}

    @staticmethod
    async def account_pending_purchases(db: AsyncSession, tenant_id: str):
        await AccountingService.init_default_accounts(db, tenant_id)
        
        stmt = select(Purchase).where(
            Purchase.status == PurchaseStatus.COMPLETED,
            Purchase.is_accounted == False,
            Purchase.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        purchases = result.scalars().all()
        
        if not purchases:
            return {"message": "No hay compras pendientes de contabilizar."}
            
        total_cash = sum(p.total for p in purchases if p.payment_method != "credit")
        total_credit = sum(p.total for p in purchases if p.payment_method == "credit")
        total_expense = total_cash + total_credit
        
        # Get accounts
        acc_stmt = select(Account).where(Account.tenant_id == tenant_id)
        accounts = (await db.execute(acc_stmt)).scalars().all()
        caja = next((a for a in accounts if a.code == "1000"), None)
        cxp = next((a for a in accounts if a.code == "2000"), None)
        gastos = next((a for a in accounts if a.code == "5000"), None)
        
        if not caja or not gastos or not cxp:
            raise HTTPException(status_code=500, detail="Cuentas contables por defecto no encontradas (Caja, CxP o Gastos)")
            
        je = JournalEntry(
            reference="Compras Pendientes",
            description=f"Contabilización de {len(purchases)} compras",
            tenant_id=tenant_id
        )
        db.add(je)
        await db.flush()
        
        # Details
        db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=gastos.id, debit=total_expense, tenant_id=tenant_id))
        gastos.balance += total_expense
        
        if total_cash > 0:
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=caja.id, credit=total_cash, tenant_id=tenant_id))
            caja.balance -= total_cash
            
        if total_credit > 0:
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=cxp.id, credit=total_credit, tenant_id=tenant_id))
            cxp.balance += total_credit
        
        for p in purchases:
            p.is_accounted = True
            
        await db.commit()
        return {"message": f"Contabilizadas {len(purchases)} compras por un total de ${total_expense}"}

    @staticmethod
    async def account_treasury_payment(db: AsyncSession, payment_id: int, tenant_id: str):
        from app.domain.treasury import TreasuryPayment
        
        result = await db.execute(
            select(TreasuryPayment).where(TreasuryPayment.id == payment_id, TreasuryPayment.tenant_id == tenant_id)
        )
        payment = result.scalars().first()
        if not payment: return
        
        acc_stmt = select(Account).where(Account.tenant_id == tenant_id)
        accounts = (await db.execute(acc_stmt)).scalars().all()
        
        caja = next((a for a in accounts if a.code == "1000"), None)
        cxc = next((a for a in accounts if a.code == "1100"), None)
        cxp = next((a for a in accounts if a.code == "2000"), None)
        
        je = JournalEntry(
            reference=f"Pago Tesorería #{payment.id}",
            description=f"Pago por {payment.amount} vía {payment.payment_method}",
            tenant_id=tenant_id
        )
        db.add(je)
        await db.flush()
        
        if payment.ar_id: # Recibiendo dinero de un cliente (CxC)
            # Debita Caja, Acredita CxC
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=caja.id, debit=payment.amount, tenant_id=tenant_id))
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=cxc.id, credit=payment.amount, tenant_id=tenant_id))
            caja.balance += payment.amount
            cxc.balance -= payment.amount
        elif payment.ap_id: # Pagando a un proveedor (CxP)
            # Debita CxP, Acredita Caja
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=cxp.id, debit=payment.amount, tenant_id=tenant_id))
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=caja.id, credit=payment.amount, tenant_id=tenant_id))
            cxp.balance -= payment.amount
            caja.balance -= payment.amount
            
        await db.flush()
