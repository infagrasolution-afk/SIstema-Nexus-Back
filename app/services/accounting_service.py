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

            # Cuentas de Nómina y Leyes Laborales (LOTTT / IVSS / BANAVIH)
            Account(code="2170", name="Retenciones SSO por Enterar (IVSS 4%)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="2171", name="Retenciones FAOV por Enterar (BANAVIH 1%)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="2172", name="Retenciones RPE por Enterar (Paro Forzoso 0.5%)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="2180", name="Sueldos y Salarios por Pagar (Nómina)", type=AccountType.LIABILITY, tenant_id=tenant_id),
            Account(code="5101", name="Gastos de Sueldos y Salarios (LOTTT)", type=AccountType.EXPENSE, tenant_id=tenant_id),
            Account(code="5102", name="Gastos de Cestaticket Socialista", type=AccountType.EXPENSE, tenant_id=tenant_id),
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
    async def account_commercial_note(db: AsyncSession, note_id: int, tenant_id: str):
        from app.domain.accounting import DebitNote
        await AccountingService.init_default_accounts(db, tenant_id)
        
        result = await db.execute(
            select(DebitNote).where(DebitNote.id == note_id, DebitNote.tenant_id == tenant_id)
        )
        note = result.scalars().first()
        
        if not note:
            raise HTTPException(status_code=404, detail="Nota comercial no encontrada")
            
        acc_stmt = select(Account).where(Account.tenant_id == tenant_id)
        accounts = (await db.execute(acc_stmt)).scalars().all()
        cxc = next((a for a in accounts if a.code == "1100"), None) # Cuentas por Cobrar
        ingresos = next((a for a in accounts if a.code == "4000"), None) # Ingresos
        
        if not cxc or not ingresos:
            raise HTTPException(status_code=500, detail="Cuentas contables por defecto no encontradas (CxC o Ingresos)")
            
        je = JournalEntry(
            reference=note.number,
            description=f"Nota de {note.type} aplicada al cliente",
            tenant_id=tenant_id
        )
        db.add(je)
        await db.flush()
        
        if note.type == 'Débito':
            # + CxC (Débito), + Ingreso (Crédito)
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=cxc.id, debit=note.amount, tenant_id=tenant_id))
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=ingresos.id, credit=note.amount, tenant_id=tenant_id))
            cxc.balance += note.amount
            ingresos.balance += note.amount
        else: # Crédito
            # - Ingreso (Débito), - CxC (Crédito)
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=ingresos.id, debit=note.amount, tenant_id=tenant_id))
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=cxc.id, credit=note.amount, tenant_id=tenant_id))
            ingresos.balance -= note.amount
            cxc.balance -= note.amount
            
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

    @staticmethod
    async def get_pnl(db: AsyncSession, tenant_id: str, start_date: str = None, end_date: str = None):
        """
        Generates a Profit & Loss (Estado de Resultados) report.
        For a simple P&L, we take the current balances of Revenue and Expense accounts.
        If date filtering is needed, we would query JournalEntryDetail joined with JournalEntry.
        """
        await AccountingService.init_default_accounts(db, tenant_id)
        
        # Simplest approach: group by account type
        stmt = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.type.in_([AccountType.REVENUE, AccountType.EXPENSE])
        ).order_by(Account.code)
        
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        
        revenues = []
        expenses = []
        total_revenue = 0.0
        total_expense = 0.0
        
        for acc in accounts:
            if acc.type == AccountType.REVENUE:
                revenues.append({"code": acc.code, "name": acc.name, "balance": acc.balance})
                total_revenue += acc.balance
            else:
                expenses.append({"code": acc.code, "name": acc.name, "balance": acc.balance})
                total_expense += acc.balance
                
        net_income = total_revenue - total_expense
        
        return {
            "revenues": revenues,
            "expenses": expenses,
            "total_revenue": total_revenue,
            "total_expense": total_expense,
            "net_income": net_income
        }

    @staticmethod
    async def account_payroll_period(db: AsyncSession, period_id: int, tenant_id: str):
        """
        Contabiliza automáticamente un período de nómina cerrado según VEN-NIF:
        - Débito: Gastos de Sueldos (5101) + Gastos Cestaticket (5102)
        - Crédito: Retención SSO 4% (2170) + Retención FAOV 1% (2171) + Retención RPE 0.5% (2172) + Sueldos por Pagar (2180)
        """
        from app.domain.payroll import PayrollPeriod, PayrollReceipt
        from sqlalchemy.orm import selectinload
        from decimal import Decimal

        await AccountingService.init_default_accounts(db, tenant_id)

        stmt = (
            select(PayrollPeriod)
            .where(PayrollPeriod.id == period_id, PayrollPeriod.tenant_id == tenant_id)
            .options(selectinload(PayrollPeriod.receipts))
        )
        res = await db.execute(stmt)
        period = res.scalars().first()
        if not period or not period.receipts:
            return None

        # Obtener cuentas contables requeridas
        acc_stmt = select(Account).where(Account.tenant_id == tenant_id)
        accounts = (await db.execute(acc_stmt)).scalars().all()

        gasto_sueldos = next((a for a in accounts if a.code == "5101"), None)
        gasto_cesta = next((a for a in accounts if a.code == "5102"), None)
        ret_sso = next((a for a in accounts if a.code == "2170"), None)
        ret_faov = next((a for a in accounts if a.code == "2171"), None)
        ret_rpe = next((a for a in accounts if a.code == "2172"), None)
        sueldos_pagar = next((a for a in accounts if a.code == "2180"), None)

        if not all([gasto_sueldos, gasto_cesta, ret_sso, ret_faov, ret_rpe, sueldos_pagar]):
            # Si alguna cuenta falta, usamos cuentas padre
            gastos_gen = next((a for a in accounts if a.code == "5000"), None)
            pasivos_gen = next((a for a in accounts if a.code == "2000"), None)
            gasto_sueldos = gasto_sueldos or gastos_gen
            gasto_cesta = gasto_cesta or gastos_gen
            ret_sso = ret_sso or pasivos_gen
            ret_faov = ret_faov or pasivos_gen
            ret_rpe = ret_rpe or pasivos_gen
            sueldos_pagar = sueldos_pagar or pasivos_gen

        tot_salarios = sum(Decimal(str(r.base_salary_ves or 0)) for r in period.receipts)
        tot_cesta = sum(Decimal(str(r.cestaticket_ves or 0)) for r in period.receipts)
        tot_sso = sum(Decimal(str(r.sso_deduction_ves or 0)) for r in period.receipts)
        tot_faov = sum(Decimal(str(r.faov_deduction_ves or 0)) for r in period.receipts)
        tot_rpe = sum(Decimal(str(r.rpe_deduction_ves or 0)) for r in period.receipts)
        tot_neto = sum(Decimal(str(r.net_amount_ves or 0)) for r in period.receipts)

        je = JournalEntry(
            reference=f"NOM-{period.code}",
            description=f"Contabilización de Nómina Período: {period.name} ({len(period.receipts)} trabajadores)",
            currency="VES",
            exchange_rate=period.exchange_rate,
            tenant_id=tenant_id
        )
        db.add(je)
        await db.flush()

        # DÉBITOS (Gastos)
        if tot_salarios > Decimal('0'):
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=gasto_sueldos.id, debit=tot_salarios, credit=Decimal('0'), tenant_id=tenant_id))
            gasto_sueldos.balance += tot_salarios

        if tot_cesta > Decimal('0'):
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=gasto_cesta.id, debit=tot_cesta, credit=Decimal('0'), tenant_id=tenant_id))
            gasto_cesta.balance += tot_cesta

        # CRÉDITOS (Retenciones de Ley y Neto por Pagar)
        if tot_sso > Decimal('0'):
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=ret_sso.id, debit=Decimal('0'), credit=tot_sso, tenant_id=tenant_id))
            ret_sso.balance += tot_sso

        if tot_faov > Decimal('0'):
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=ret_faov.id, debit=Decimal('0'), credit=tot_faov, tenant_id=tenant_id))
            ret_faov.balance += tot_faov

        if tot_rpe > Decimal('0'):
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=ret_rpe.id, debit=Decimal('0'), credit=tot_rpe, tenant_id=tenant_id))
            ret_rpe.balance += tot_rpe

        if tot_neto > Decimal('0'):
            db.add(JournalEntryDetail(journal_entry_id=je.id, account_id=sueldos_pagar.id, debit=Decimal('0'), credit=tot_neto, tenant_id=tenant_id))
            sueldos_pagar.balance += tot_neto

        await db.flush()
        return je

    @staticmethod
    async def get_trial_balance(db: AsyncSession, tenant_id: str):
        """
        Genera el Balance de Comprobación de Sumas y Saldos (Trial Balance) según VEN-NIF.
        Calcula Suma Débitos, Suma Créditos, Saldo Deudor y Saldo Acreedor por cuenta.
        """
        from sqlalchemy import func
        await AccountingService.init_default_accounts(db, tenant_id)

        # Consultar todas las cuentas activas
        stmt = select(Account).where(Account.tenant_id == tenant_id, Account.is_active == True).order_by(Account.code.asc())
        accounts = (await db.execute(stmt)).scalars().all()

        # Consultar sumas acumuladas de débitos y créditos en JournalEntryDetail
        detail_stmt = (
            select(
                JournalEntryDetail.account_id,
                func.sum(JournalEntryDetail.debit).label("total_debit"),
                func.sum(JournalEntryDetail.credit).label("total_credit")
            )
            .join(JournalEntry, JournalEntry.id == JournalEntryDetail.journal_entry_id)
            .where(
                JournalEntryDetail.tenant_id == tenant_id,
                JournalEntry.status == "POSTED"
            )
            .group_by(JournalEntryDetail.account_id)
        )
        detail_res = await db.execute(detail_stmt)
        sums_by_account = {row[0]: (row[1] or Decimal('0'), row[2] or Decimal('0')) for row in detail_res.all()}

        rows = []
        sum_total_debit = Decimal('0')
        sum_total_credit = Decimal('0')
        sum_saldo_deudor = Decimal('0')
        sum_saldo_acreedor = Decimal('0')

        for acc in accounts:
            tot_deb, tot_cred = sums_by_account.get(acc.id, (Decimal('0'), Decimal('0')))
            diff = tot_deb - tot_cred

            # En VEN-NIF: Activos y Gastos son de naturaleza deudora; Pasivos, Capital e Ingresos son de naturaleza acreedora
            if diff >= Decimal('0'):
                saldo_deudor = diff
                saldo_acreedor = Decimal('0')
            else:
                saldo_deudor = Decimal('0')
                saldo_acreedor = abs(diff)

            sum_total_debit += tot_deb
            sum_total_credit += tot_cred
            sum_saldo_deudor += saldo_deudor
            sum_saldo_acreedor += saldo_acreedor

            rows.append({
                "account_id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "type": acc.type,
                "total_debit": float(tot_deb),
                "total_credit": float(tot_cred),
                "debit_balance": float(saldo_deudor),
                "credit_balance": float(saldo_acreedor)
            })

        is_balanced = abs(sum_total_debit - sum_total_credit) < Decimal('0.01') and abs(sum_saldo_deudor - sum_saldo_acreedor) < Decimal('0.01')

        return {
            "rows": rows,
            "total_debit_sum": float(sum_total_debit),
            "total_credit_sum": float(sum_total_credit),
            "total_debit_balance": float(sum_saldo_deudor),
            "total_credit_balance": float(sum_saldo_acreedor),
            "is_balanced": is_balanced
        }

    @staticmethod
    async def get_balance_sheet(db: AsyncSession, tenant_id: str):
        """
        Genera el Estado de Situación Financiera (Balance General) VEN-NIF.
        Ecuación: Activo = Pasivo + Patrimonio + Utilidad del Ejercicio
        """
        await AccountingService.init_default_accounts(db, tenant_id)

        stmt = select(Account).where(Account.tenant_id == tenant_id, Account.is_active == True).order_by(Account.code.asc())
        accounts = (await db.execute(stmt)).scalars().all()

        assets = []
        liabilities = []
        equity = []
        total_assets = Decimal('0')
        total_liabilities = Decimal('0')
        total_equity = Decimal('0')

        # Primero obtenemos el P&L actual para incorporar la utilidad neta no cerrada
        pnl = await AccountingService.get_pnl(db, tenant_id)
        current_year_earnings = Decimal(str(pnl.get("net_income", 0)))

        for acc in accounts:
            bal = Decimal(str(acc.balance or 0))
            item = {"code": acc.code, "name": acc.name, "balance": float(bal)}

            if acc.type == AccountType.ASSET:
                assets.append(item)
                total_assets += bal
            elif acc.type == AccountType.LIABILITY:
                liabilities.append(item)
                total_liabilities += bal
            elif acc.type == AccountType.EQUITY:
                equity.append(item)
                total_equity += bal

        total_equity_with_earnings = total_equity + current_year_earnings
        total_liab_plus_equity = total_liabilities + total_equity_with_earnings
        equation_balanced = abs(total_assets - total_liab_plus_equity) < Decimal('0.01')

        return {
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "current_year_earnings": float(current_year_earnings),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "total_equity": float(total_equity),
            "total_liabilities_and_equity": float(total_liab_plus_equity),
            "equation_balanced": equation_balanced
        }

    @staticmethod
    async def close_fiscal_year(db: AsyncSession, year: int, tenant_id: str):
        """
        Ejecuta el Asiento de Cierre de Ejercicio Económico (Refundición de Cuentas Nominales):
        - Cancela todos los Ingresos (4xxx) debitándolos.
        - Cancela todos los Gastos/Costos (5xxx) acreditándolos.
        - Transfiere el resultado neto a la cuenta de Patrimonio '3201 - Resultado del Ejercicio'.
        """
        await AccountingService.init_default_accounts(db, tenant_id)

        # Buscar o crear cuenta de Resultados del Ejercicio (3201)
        acc_stmt = select(Account).where(Account.tenant_id == tenant_id)
        accounts = (await db.execute(acc_stmt)).scalars().all()

        res_account = next((a for a in accounts if a.code == "3201"), None)
        if not res_account:
            res_account = Account(
                code="3201",
                name="Resultados del Ejercicio Económico (Superávit/Déficit)",
                type=AccountType.EQUITY,
                balance=Decimal('0.0000'),
                tenant_id=tenant_id
            )
            db.add(res_account)
            await db.flush()

        # Obtener cuentas de Ingresos y Gastos con saldo
        rev_exp_accounts = [a for a in accounts if a.type in (AccountType.REVENUE, AccountType.EXPENSE) and a.balance != Decimal('0')]
        if not rev_exp_accounts:
            return {"message": f"No hay saldos en cuentas nominales para cerrar el ejercicio {year}."}

        total_rev = Decimal('0')
        total_exp = Decimal('0')

        closing_je = JournalEntry(
            reference=f"CIERRE-{year}",
            description=f"Asiento de Cierre de Cuentas Nominales del Ejercicio Fiscal {year}",
            currency="USD",
            exchange_rate=Decimal('1.0000'),
            tenant_id=tenant_id
        )
        db.add(closing_je)
        await db.flush()

        for a in rev_exp_accounts:
            bal = a.balance
            if a.type == AccountType.REVENUE:
                # Cancelar ingreso (débito)
                db.add(JournalEntryDetail(journal_entry_id=closing_je.id, account_id=a.id, debit=bal, credit=Decimal('0'), tenant_id=tenant_id))
                total_rev += bal
                a.balance = Decimal('0.0000')
            elif a.type == AccountType.EXPENSE:
                # Cancelar gasto (crédito)
                db.add(JournalEntryDetail(journal_entry_id=closing_je.id, account_id=a.id, debit=Decimal('0'), credit=bal, tenant_id=tenant_id))
                total_exp += bal
                a.balance = Decimal('0.0000')

        net_result = total_rev - total_exp
        if net_result > Decimal('0'):
            # Ganancia neta -> Crédito a Resultados del Ejercicio
            db.add(JournalEntryDetail(journal_entry_id=closing_je.id, account_id=res_account.id, debit=Decimal('0'), credit=net_result, tenant_id=tenant_id))
            res_account.balance += net_result
        elif net_result < Decimal('0'):
            # Pérdida neta -> Débito a Resultados del Ejercicio
            db.add(JournalEntryDetail(journal_entry_id=closing_je.id, account_id=res_account.id, debit=abs(net_result), credit=Decimal('0'), tenant_id=tenant_id))
            res_account.balance -= abs(net_result)

        await db.commit()
        return {
            "message": f"Ejercicio fiscal {year} cerrado exitosamente.",
            "closing_journal_entry_id": closing_je.id,
            "total_revenues_closed": float(total_rev),
            "total_expenses_closed": float(total_exp),
            "net_result": float(net_result)
        }

