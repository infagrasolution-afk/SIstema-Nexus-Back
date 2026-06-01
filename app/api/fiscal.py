import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime

from app.api.deps import get_current_tenant, get_master_db, get_current_user
from app.domain.sales import Sale
from app.domain.purchases import Purchase
from app.domain.user import User

router = APIRouter()

@router.get("/libro-ventas")
async def get_libro_ventas(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Exporta el Libro de Ventas en formato oficial SENIAT (Venezuela) en CSV.
    """
    if not month:
        month = datetime.utcnow().month
    if not year:
        year = datetime.utcnow().year

    # Cargar ventas completadas del inquilino para el mes/año seleccionado
    stmt = select(Sale).options(selectinload(Sale.customer)).where(
        Sale.tenant_id == tenant_id,
        Sale.status == "COMPLETED"
    )
    
    result = await db.execute(stmt)
    all_sales = result.scalars().all()
    
    # Filtrar localmente por mes y año
    sales = [
        s for s in all_sales 
        if s.created_at.month == month and s.created_at.year == year
    ]

    output = io.StringIO()
    output.write('\ufeff') # UTF-8 BOM for Excel
    writer = csv.writer(output, delimiter=';')
    
    # Encabezado Corporativo del Libro Fiscal
    writer.writerow(["LIBRO DE VENTAS FISCAL (SENIAT VENEZUELA)"])
    writer.writerow([f"Período Tributario: {month:02d}/{year}"])
    writer.writerow([f"Inquilino ID: {tenant_id}"])
    writer.writerow([])
    
    # Cabeceras oficiales exigidas por el SENIAT
    writer.writerow([
        "Oper. Nro.",
        "Fecha Factura",
        "R.I.F. / C.I.",
        "Nombre o Razón Social",
        "Nro. Factura",
        "Nro. Control",
        "Nro. Nota Crédito",
        "Nro. Nota Débito",
        "Tipo Transac.",
        "Factura Afectada",
        "Total Ventas con IVA (Bs/USD)",
        "Ventas Exentas o Exoneradas",
        "Base Imponible (General 16%)",
        "% Alícuota General",
        "Impuesto I.V.A. (General 16%)",
        "Base Imponible (Reducida 8%)",
        "% Alícuota Reducida",
        "Impuesto I.V.A. (Reducido 8%)",
        "I.V.A. Retenido (por el Cliente)",
        "Nro. Comprobante Retención",
        "Fecha Comprobante"
    ])
    
    for idx, sale in enumerate(sales, 1):
        total = sale.total
        tax_total = sale.tax_total
        subtotal = sale.subtotal
        
        rif = sale.customer.tax_id if sale.customer else "V-00000000-0"
        name = sale.customer.name if sale.customer else "Consumidor Final"
        invoice_num = sale.fiscal_invoice_number or f"FAC-{sale.id:06d}"
        control_num = f"CON-{sale.id:06d}"
        
        exempt_amount = 0.0
        taxable_base = 0.0
        iva_amount = 0.0
        
        if tax_total > 0.01:
            taxable_base = subtotal
            iva_amount = tax_total
        else:
            exempt_amount = total
            
        writer.writerow([
            idx,
            sale.created_at.strftime("%d/%m/%Y"),
            rif,
            name,
            invoice_num,
            control_num,
            "",
            "",
            "01-REG",
            "",
            f"{total:.2f}",
            f"{exempt_amount:.2f}",
            f"{taxable_base:.2f}",
            "16%" if taxable_base > 0 else "0%",
            f"{iva_amount:.2f}",
            "0.00",
            "8%",
            "0.00",
            "0.00",
            "",
            ""
        ])
        
    response = StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=libro_ventas_{month:02d}_{year}.csv"
    return response

@router.get("/libro-compras")
async def get_libro_compras(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Exporta el Libro de Compras en formato oficial SENIAT (Venezuela) en CSV.
    """
    if not month:
        month = datetime.utcnow().month
    if not year:
        year = datetime.utcnow().year

    # Cargar compras completadas del inquilino para el mes/año seleccionado
    stmt = select(Purchase).options(selectinload(Purchase.supplier)).where(
        Purchase.tenant_id == tenant_id,
        Purchase.status == "COMPLETED"
    )
    
    result = await db.execute(stmt)
    all_purchases = result.scalars().all()
    
    # Filtrar por mes/año localmente
    purchases = [
        p for p in all_purchases 
        if p.created_at.month == month and p.created_at.year == year
    ]

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    
    # Encabezado Corporativo
    writer.writerow(["LIBRO DE COMPRAS FISCAL (SENIAT VENEZUELA)"])
    writer.writerow([f"Período Tributario: {month:02d}/{year}"])
    writer.writerow([f"Inquilino ID: {tenant_id}"])
    writer.writerow([])
    
    # Cabeceras oficiales exigidas por el SENIAT
    writer.writerow([
        "Oper. Nro.",
        "Fecha Factura",
        "R.I.F. Proveedor",
        "Nombre o Razón Social Proveedor",
        "Nro. Factura Proveedor",
        "Nro. Control Factura",
        "Nro. Nota Crédito",
        "Nro. Nota Débito",
        "Tipo Transac.",
        "Factura Afectada",
        "Total Compras con IVA (Bs/USD)",
        "Compras Exentas o Sin Derecho Crédito",
        "Base Imponible (General 16%)",
        "% Alícuota General",
        "Impuesto I.V.A. (General 16%)",
        "Base Imponible (Reducida 8%)",
        "% Alícuota Reducida",
        "Impuesto I.V.A. (Reducido 8%)",
        "I.V.A. Retenido (por la Empresa)",
        "Nro. Comprobante Retención",
        "Fecha Comprobante"
    ])
    
    for idx, purchase in enumerate(purchases, 1):
        total = purchase.total
        tax_total = purchase.tax_total
        subtotal = purchase.subtotal
        
        rif = purchase.supplier.tax_id if purchase.supplier else "J-00000000-0"
        name = purchase.supplier.name if purchase.supplier else "Proveedor Desconocido"
        invoice_num = purchase.reference or f"COMP-{purchase.id:06d}"
        control_num = f"CON-{purchase.id:06d}"
        
        exempt_amount = 0.0
        taxable_base = 0.0
        iva_amount = 0.0
        
        if tax_total > 0.01:
            taxable_base = subtotal
            iva_amount = tax_total
        else:
            exempt_amount = total
            
        writer.writerow([
            idx,
            purchase.created_at.strftime("%d/%m/%Y"),
            rif,
            name,
            invoice_num,
            control_num,
            "",
            "",
            "01-REG",
            "",
            f"{total:.2f}",
            f"{exempt_amount:.2f}",
            f"{taxable_base:.2f}",
            "16%" if taxable_base > 0 else "0%",
            f"{iva_amount:.2f}",
            "0.00",
            "8%",
            "0.00",
            "0.00",
            "",
            ""
        ])
        
    response = StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=libro_compras_{month:02d}_{year}.csv"
    return response
