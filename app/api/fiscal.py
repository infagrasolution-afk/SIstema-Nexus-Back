import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, extract
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timezone

from app.api.deps import get_current_tenant, get_db, get_master_db, get_current_user, require_module
from app.domain.sales import Sale, CreditNote
from app.domain.purchases import Purchase
from app.domain.tenant import Tenant
from app.domain.user import User
from app.services.pdf_service import PDFService

router = APIRouter(dependencies=[Depends(require_module("fiscal"))])


# ─────────────────────────────────────────────────────────────────────────────
# 1. LIBRO DE VENTAS FISCAL SENIAT (CSV / EXCEL)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/libro-ventas")
async def get_libro_ventas(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    master_db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Exporta el Libro de Ventas en formato oficial SENIAT (Venezuela) en CSV con BOM para Excel.
    Incluye facturas de venta y notas de crédito que rebajan débito fiscal.
    """
    now = datetime.now(timezone.utc)
    if not month:
        month = now.month
    if not year:
        year = now.year

    # Obtener datos fiscales del inquilino
    tenant_res = await master_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalars().first()

    # 1. Facturas de Venta
    sales_stmt = select(Sale).options(selectinload(Sale.customer)).where(
        Sale.tenant_id == tenant_id,
        Sale.status == "COMPLETED",
        extract('month', Sale.created_at) == month,
        extract('year', Sale.created_at) == year,
    ).order_by(Sale.created_at.asc())
    sales_res = await db.execute(sales_stmt)
    sales = sales_res.scalars().all()

    # 2. Notas de Crédito emitidas
    cn_stmt = select(CreditNote).where(
        CreditNote.tenant_id == tenant_id,
        CreditNote.status == "APPROVED",
        extract('month', CreditNote.created_at) == month,
        extract('year', CreditNote.created_at) == year,
    ).order_by(CreditNote.created_at.asc())
    cn_res = await db.execute(cn_stmt)
    credit_notes = cn_res.scalars().all()

    output = io.StringIO()
    output.write('\ufeff') # UTF-8 BOM for Excel
    writer = csv.writer(output, delimiter=';')
    
    # Encabezado Corporativo del Libro Fiscal
    writer.writerow(["LIBRO DE VENTAS FISCAL (SENIAT VENEZUELA)"])
    writer.writerow([f"Razón Social: {tenant.name if tenant else 'NEXUS ERP'}", f"R.I.F.: {tenant.tax_id if tenant else 'J-00000000-0'}"])
    writer.writerow([f"Período Tributario: {month:02d}/{year}"])
    writer.writerow([])
    
    # Cabeceras oficiales exigidas por el SENIAT
    writer.writerow([
        "Oper. Nro.",
        "Fecha Documento",
        "R.I.F. / C.I.",
        "Nombre o Razón Social del Cliente",
        "Nro. Factura",
        "Nro. Control Fiscal",
        "Nro. Nota Crédito",
        "Nro. Nota Débito",
        "Tipo Transac.",
        "Factura Afectada",
        "Total Ventas con IVA",
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
    
    oper_num = 1

    # Escribir Facturas
    for sale in sales:
        total = float(sale.total or 0.0)
        tax_total = float(sale.tax_total or 0.0)
        subtotal = float(sale.subtotal or 0.0)
        
        rif = sale.customer.tax_id if sale.customer else "V-00000000-0"
        name = sale.customer.name if sale.customer else "Consumidor Final"
        invoice_num = sale.fiscal_invoice_number or f"FAC-{sale.id:06d}"
        control_num = sale.control_number or f"00-{sale.id:06d}"
        
        exempt_amount = 0.0
        taxable_base = 0.0
        iva_amount = 0.0
        
        if tax_total > 0.01:
            taxable_base = subtotal
            iva_amount = tax_total
        else:
            exempt_amount = total
            
        writer.writerow([
            oper_num,
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
        oper_num += 1

    # Escribir Notas de Crédito (Restan Débito Fiscal)
    for cn in credit_notes:
        total = float(cn.total or 0.0)
        tax_total = float(cn.tax_total or 0.0)
        subtotal = float(cn.subtotal or 0.0)
        
        writer.writerow([
            oper_num,
            cn.created_at.strftime("%d/%m/%Y"),
            "V-00000000-0",
            "Nota de Crédito por Devolución/Descuento",
            "",
            cn.control_number or "",
            cn.number,
            "",
            "03-NC",
            f"FAC-{cn.sale_id:06d}",
            f"-{total:.2f}",
            "0.00",
            f"-{subtotal:.2f}",
            "16%",
            f"-{tax_total:.2f}",
            "0.00",
            "8%",
            "0.00",
            "0.00",
            "",
            ""
        ])
        oper_num += 1
        
    response = StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=libro_ventas_{month:02d}_{year}.csv"
    return response


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIBRO DE COMPRAS FISCAL SENIAT (CSV / EXCEL)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/libro-compras")
async def get_libro_compras(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    master_db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Exporta el Libro de Compras en formato oficial SENIAT (Venezuela) en CSV con BOM para Excel.
    """
    now = datetime.now(timezone.utc)
    if not month:
        month = now.month
    if not year:
        year = now.year

    tenant_res = await master_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalars().first()

    stmt = select(Purchase).options(selectinload(Purchase.supplier)).where(
        Purchase.tenant_id == tenant_id,
        Purchase.status == "COMPLETED",
        extract('month', Purchase.created_at) == month,
        extract('year', Purchase.created_at) == year,
    ).order_by(Purchase.created_at.asc())

    result = await db.execute(stmt)
    purchases = result.scalars().all()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';')
    
    # Encabezado Corporativo
    writer.writerow(["LIBRO DE COMPRAS FISCAL (SENIAT VENEZUELA)"])
    writer.writerow([f"Razón Social: {tenant.name if tenant else 'NEXUS ERP'}", f"R.I.F.: {tenant.tax_id if tenant else 'J-00000000-0'}"])
    writer.writerow([f"Período Tributario: {month:02d}/{year}"])
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
        "Total Compras con IVA",
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
        total = float(purchase.total or 0.0)
        tax_total = float(purchase.tax_total or 0.0)
        subtotal = float(purchase.subtotal or 0.0)
        iva_withholding = float(purchase.iva_withholding or 0.0)
        
        rif = purchase.supplier.tax_id if purchase.supplier else "J-00000000-0"
        name = purchase.supplier.name if purchase.supplier else "Proveedor Desconocido"
        invoice_num = purchase.invoice_number or purchase.reference or f"COMP-{purchase.id:06d}"
        control_num = purchase.control_number or f"00-{purchase.id:06d}"
        
        exempt_amount = 0.0
        taxable_base = 0.0
        iva_amount = 0.0
        
        if tax_total > 0.01:
            taxable_base = subtotal
            iva_amount = tax_total
        else:
            exempt_amount = total

        voucher_num = f"{purchase.created_at.strftime('%Y%m')}{purchase.id:08d}" if iva_withholding > 0 else ""
        voucher_date = purchase.created_at.strftime("%d/%m/%Y") if iva_withholding > 0 else ""
            
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
            f"{iva_withholding:.2f}",
            voucher_num,
            voucher_date
        ])
        
    response = StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8-sig')), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=libro_compras_{month:02d}_{year}.csv"
    return response


# ─────────────────────────────────────────────────────────────────────────────
# 3. ARCHIVO TXT OFICIAL SENIAT PARA DECLARACIÓN DE RETENCIONES IVA
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/txt-retenciones-iva")
async def get_txt_retenciones_seniat(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    master_db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Genera el archivo TXT estructurado que exige el portal web del SENIAT
    para cargar la declaración de retenciones de IVA a proveedores.
    Formato estándar SENIAT:
    RIF_Agente(10)|Periodo(6)|FechaFactura(10)|TipoOperacion(1)|TipoDoc(2)|RIF_Proveedor(10)|NroFactura|NroControl|Total|Base|IvaRetenido|DocAfectado|NroComprobante(14)|Exento|Alicuota|NroExpediente
    """
    now = datetime.now(timezone.utc)
    if not month:
        month = now.month
    if not year:
        year = now.year

    tenant_res = await master_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalars().first()

    raw_agent_rif = (tenant.tax_id if tenant and tenant.tax_id else "J000000000").replace("-", "").strip().upper()
    period_str = f"{year}{month:02d}"

    stmt = select(Purchase).options(selectinload(Purchase.supplier)).where(
        Purchase.tenant_id == tenant_id,
        Purchase.status == "COMPLETED",
        Purchase.iva_withholding > 0,
        extract('month', Purchase.created_at) == month,
        extract('year', Purchase.created_at) == year,
    ).order_by(Purchase.created_at.asc())

    result = await db.execute(stmt)
    purchases = result.scalars().all()

    txt_lines = []
    for p in purchases:
        supplier_rif = (p.supplier.tax_id if p.supplier and p.supplier.tax_id else "J000000000").replace("-", "").strip().upper()
        invoice_date = p.created_at.strftime("%Y-%m-%d")
        invoice_num = p.invoice_number or p.reference or str(p.id)
        control_num = p.control_number or f"00-{p.id:06d}"
        total_str = f"{float(p.total or 0):.2f}"
        base_str = f"{float(p.subtotal or 0):.2f}"
        ret_str = f"{float(p.iva_withholding or 0):.2f}"
        voucher_num = f"{p.created_at.strftime('%Y%m')}{p.id:08d}"

        # Estructura oficial del SENIAT separada por tabulador o salto de línea
        line = f"{raw_agent_rif}\t{period_str}\t{invoice_date}\tC\t01\t{supplier_rif}\t{invoice_num}\t{control_num}\t{total_str}\t{base_str}\t{ret_str}\t0\t{voucher_num}\t0.00\t16.00\t0"
        txt_lines.append(line)

    txt_content = "\r\n".join(txt_lines)
    return Response(
        content=txt_content.encode("latin-1", errors="replace"),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=retenciones_iva_{period_str}.txt"}
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. COMPROBANTE DE RETENCIÓN DE IVA EN PDF OFICIAL (SNAT/2015/0049)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/comprobante-iva/{purchase_id}")
async def get_comprobante_retencion_pdf(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    master_db: AsyncSession = Depends(get_master_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user)
):
    """
    Genera y descarga el Comprobante de Retención de IVA en PDF oficial
    según Providencia Administrativa SNAT/2015/0049 para una compra a proveedor.
    """
    stmt = (
        select(Purchase)
        .where(Purchase.id == purchase_id, Purchase.tenant_id == tenant_id)
        .options(selectinload(Purchase.supplier))
    )
    result = await db.execute(stmt)
    purchase = result.scalars().first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Compra no encontrada")

    tenant_res = await master_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalars().first()

    pdf_buffer = PDFService.generate_withholding_voucher(purchase, tenant)
    voucher_num = f"{purchase.created_at.strftime('%Y%m')}{purchase.id:08d}"

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comprobante_iva_{voucher_num}.pdf"}
    )
