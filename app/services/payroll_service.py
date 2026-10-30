from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domain.payroll import Employee, PayrollPeriod, PayrollReceipt, PayrollPeriodStatus

class PayrollService:
    @staticmethod
    async def calculate_period(
        db: AsyncSession,
        period_id: int,
        tenant_id: int,
        cestaticket_usd_month: Decimal = Decimal('40.0000') # Cestaticket de ley indexado
    ) -> PayrollPeriod:
        """
        Calcula la nómina del período para todos los empleados activos del tenant
        aplicando la normativa laboral venezolana (LOTTT, IVSS, Banavih).
        """
        # 1. Obtener período
        period_stmt = select(PayrollPeriod).where(
            PayrollPeriod.id == period_id,
            PayrollPeriod.tenant_id == tenant_id
        ).options(selectinload(PayrollPeriod.receipts))
        res = await db.execute(period_stmt)
        period = res.scalars().first()
        if not period:
            raise ValueError("Período de nómina no encontrado")

        # 2. Obtener empleados activos
        emp_stmt = select(Employee).where(
            Employee.tenant_id == tenant_id,
            Employee.is_active == True
        )
        emp_res = await db.execute(emp_stmt)
        employees = emp_res.scalars().all()

        # Limpiar recibos anteriores del período si se recalcula
        for r in period.receipts:
            await db.delete(r)
        await db.flush()

        period_gross = Decimal('0.0000')
        period_deductions = Decimal('0.0000')
        period_net = Decimal('0.0000')

        # Cestaticket quincenal por defecto ($20 quincenal)
        cestaticket_quincenal = cestaticket_usd_month / Decimal('2.0')

        for emp in employees:
            # Salario base de la quincena (la mitad del mensual)
            monthly_salary = emp.base_salary_usd
            quincena_salary = monthly_salary / Decimal('2.0')

            cesta = cestaticket_quincenal if emp.cestaticket_eligible else Decimal('0.0000')
            bonuses = Decimal('0.0000')
            overtime = Decimal('0.0000')

            gross_total = quincena_salary + cesta + bonuses + overtime

            # Deducciones de Ley (calculadas sobre el salario quincenal)
            # 1. SSO (Seguro Social Obligatorio): 4%
            sso = (quincena_salary * Decimal('0.0400')) if emp.sso_eligible else Decimal('0.0000')
            
            # 2. RPE (Régimen Prestacional de Empleo / Paro Forzoso): 0.5%
            rpe = (quincena_salary * Decimal('0.0050')) if emp.rpe_eligible else Decimal('0.0000')

            # 3. FAOV (Fondo de Ahorro Obligatorio para la Vivienda / Banavih): 1%
            faov = (quincena_salary * Decimal('0.0100')) if emp.faov_eligible else Decimal('0.0000')

            total_ded = sso + rpe + faov
            net = gross_total - total_ded
            if net < Decimal('0.0000'):
                net = Decimal('0.0000')

            receipt = PayrollReceipt(
                period_id=period.id,
                employee_id=emp.id,
                base_salary_amount=quincena_salary,
                cesta_ticket=cesta,
                bonuses=bonuses,
                overtime=overtime,
                gross_total=gross_total,
                sso_deduction=sso,
                rpe_deduction=rpe,
                faov_deduction=faov,
                other_deductions=Decimal('0.0000'),
                total_deductions=total_ded,
                net_payable=net,
                currency="USD",
                exchange_rate=period.exchange_rate,
                tenant_id=tenant_id
            )
            db.add(receipt)

            period_gross += gross_total
            period_deductions += total_ded
            period_net += net

        period.total_gross = period_gross
        period.total_deductions = period_deductions
        period.total_net = period_net
        period.status = PayrollPeriodStatus.CALCULATED.value

        await db.commit()
        await db.refresh(period)
        return period
