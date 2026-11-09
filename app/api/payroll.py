from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal

from app.api.deps import get_db, get_current_tenant, get_current_user, require_module
from app.domain.payroll import Employee, PayrollPeriod, PayrollReceipt, PayrollPeriodStatus
from app.schemas.payroll import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    PayrollPeriodCreate, PayrollPeriodResponse, PayrollReceiptResponse
)
from app.services.payroll_service import PayrollService

router = APIRouter(dependencies=[Depends(require_module("payroll"))])


# ─────────────────────────────────────────────────────────────────────────────
# 1. EMPLEADOS (FICHA DE TRABAJADOR LOTTT)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    department: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    """Lista todos los empleados de la empresa."""
    stmt = select(Employee).where(Employee.tenant_id == tenant_id).order_by(Employee.last_name.asc())
    if department:
        stmt = stmt.where(Employee.department == department)
    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    emp_in: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user = Depends(get_current_user),
):
    """Registra un nuevo trabajador."""
    new_emp = Employee(
        **emp_in.model_dump(),
        tenant_id=tenant_id,
        created_by_id=current_user.id,
        created_by_name=current_user.username
    )
    db.add(new_emp)
    await db.commit()
    await db.refresh(new_emp)
    return new_emp


@router.get("/employees/{emp_id}", response_model=EmployeeResponse)
async def get_employee(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """Obtiene el detalle de un trabajador."""
    stmt = select(Employee).where(Employee.id == emp_id, Employee.tenant_id == tenant_id)
    result = await db.execute(stmt)
    emp = result.scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return emp


@router.put("/employees/{emp_id}", response_model=EmployeeResponse)
async def update_employee(
    emp_id: int,
    emp_in: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user = Depends(get_current_user),
):
    """Actualiza la ficha laboral del trabajador."""
    stmt = select(Employee).where(Employee.id == emp_id, Employee.tenant_id == tenant_id)
    result = await db.execute(stmt)
    emp = result.scalars().first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    update_data = emp_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(emp, field, value)

    emp.updated_by_id = current_user.id
    emp.updated_by_name = current_user.username

    await db.commit()
    await db.refresh(emp)
    return emp


# ─────────────────────────────────────────────────────────────────────────────
# 2. PERÍODOS DE NÓMINA Y CÁLCULO LEGAL VENEZOLANO
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/periods", response_model=List[PayrollPeriodResponse])
async def list_periods(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """Lista todos los períodos de nómina generados."""
    stmt = (
        select(PayrollPeriod)
        .where(PayrollPeriod.tenant_id == tenant_id)
        .options(selectinload(PayrollPeriod.receipts).selectinload(PayrollReceipt.employee))
        .order_by(PayrollPeriod.payment_date.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/periods", response_model=PayrollPeriodResponse)
async def create_period(
    period_in: PayrollPeriodCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user = Depends(get_current_user),
):
    """Abre un nuevo período de nómina."""
    period = PayrollPeriod(
        **period_in.model_dump(),
        status=PayrollPeriodStatus.DRAFT.value,
        tenant_id=tenant_id,
        created_by_id=current_user.id,
        created_by_name=current_user.username
    )
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


@router.post("/periods/{period_id}/calculate", response_model=PayrollPeriodResponse)
async def calculate_payroll(
    period_id: int,
    cestaticket_usd: Optional[Decimal] = Query(Decimal('40.0000')),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """
    Ejecuta el cálculo automático de nómina LOTTT:
    - Asignaciones: Sueldo base quincenal + Cestaticket + Bonos
    - Deducciones: SSO 4%, RPE 0.5%, FAOV 1%
    """
    try:
        calculated_period = await PayrollService.calculate_period(
            db=db,
            period_id=period_id,
            tenant_id=tenant_id,
            cestaticket_usd_month=cestaticket_usd
        )
        return calculated_period
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/periods/{period_id}/close", response_model=PayrollPeriodResponse)
async def close_payroll_period(
    period_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """Cierra definitivamente un período de nómina para pago."""
    stmt = select(PayrollPeriod).where(PayrollPeriod.id == period_id, PayrollPeriod.tenant_id == tenant_id)
    res = await db.execute(stmt)
    period = res.scalars().first()
    if not period:
        raise HTTPException(status_code=404, detail="Período no encontrado")

    period.status = PayrollPeriodStatus.CLOSED.value
    
    # Contabilización automática en el Libro Diario VEN-NIF
    try:
        from app.services.accounting_service import AccountingService
        await AccountingService.account_payroll_period(db, period.id, tenant_id)
    except Exception as e:
        print(f"Aviso de contabilización de nómina: {e}")

    await db.commit()
    await db.refresh(period)
    return period


# ─────────────────────────────────────────────────────────────────────────────
# 3. RECIBO INDIVIDUAL DE PAGO (PDF LOTTT)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/receipts/{receipt_id}/pdf")
async def download_receipt_pdf(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
):
    """
    Descarga el recibo de pago de nómina formal en PDF según normativas de la LOTTT.
    """
    from fastapi.responses import Response
    from app.api.deps import get_master_db
    from app.domain.tenant import Tenant
    from app.services.pdf_service import PDFService
    from app.core.database import MasterSessionLocal

    stmt = (
        select(PayrollReceipt)
        .where(PayrollReceipt.id == receipt_id, PayrollReceipt.tenant_id == tenant_id)
        .options(selectinload(PayrollReceipt.employee), selectinload(PayrollReceipt.payroll_period))
    )
    res = await db.execute(stmt)
    receipt = res.scalars().first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recibo de nómina no encontrado")

    # Obtener datos de la empresa (Tenant)
    async with MasterSessionLocal() as master_db:
        stmt_t = select(Tenant).where(Tenant.id == tenant_id)
        res_t = await master_db.execute(stmt_t)
        tenant = res_t.scalars().first()

    pdf_buffer = PDFService.generate_payroll_receipt(
        receipt=receipt,
        employee=receipt.employee,
        period=receipt.payroll_period,
        tenant=tenant
    )

    clean_num = receipt.receipt_number.replace('/', '_').replace(' ', '_')
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=recibo_nomina_{clean_num}.pdf"
        }
    )

