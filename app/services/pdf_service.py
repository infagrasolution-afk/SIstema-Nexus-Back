import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from app.domain.sales import Sale

class PDFService:
    @staticmethod
    def generate_invoice(sale: Sale) -> io.BytesIO:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Primary Color from Tenant
        primary_color_hex = sale.tenant.primary_color if sale.tenant and sale.tenant.primary_color else "#2563eb"
        try:
            brand_color = colors.HexColor(primary_color_hex)
        except:
            brand_color = colors.HexColor("#2563eb")

        # Logo and Header
        y_header = height - 0.8 * inch
        if sale.tenant and sale.tenant.logo_url:
            try:
                # Note: ReportLab might need an external library for some image formats, 
                # but for standard URLs/Paths it should work if accessible.
                p.drawImage(sale.tenant.logo_url, 1 * inch, height - 1.2 * inch, width=1.5*inch, preserveAspectRatio=True, mask='auto')
                y_header = height - 1.3 * inch
            except Exception as e:
                print(f"Error loading logo for PDF: {e}")
                p.setFont("Helvetica-Bold", 20)
                p.setFillColor(brand_color)
                p.drawString(1 * inch, y_header, sale.tenant.name if sale.tenant else "APEX ERP")
                y_header -= 0.3 * inch
        else:
            p.setFont("Helvetica-Bold", 20)
            p.setFillColor(brand_color)
            p.drawString(1 * inch, y_header, sale.tenant.name if sale.tenant else "APEX ERP")
            y_header -= 0.3 * inch
        
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 9)
        if sale.tenant and sale.tenant.tax_id:
            p.drawString(1 * inch, y_header, f"RIF/Tax ID: {sale.tenant.tax_id}")
            y_header -= 0.15 * inch
        if sale.tenant and sale.tenant.address:
            p.drawString(1 * inch, y_header, f"Dirección: {sale.tenant.address}")
            y_header -= 0.15 * inch
        if sale.tenant and sale.tenant.phone:
            p.drawString(1 * inch, y_header, f"Teléfono: {sale.tenant.phone}")

        # Invoice Info (Right side)
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 14)
        p.drawRightString(7.5 * inch, height - 0.8 * inch, "FACTURA DE VENTA")
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 10)
        p.drawRightString(7.5 * inch, height - 1.0 * inch, f"Nro: {str(sale.id).zfill(6)}")
        p.drawRightString(7.5 * inch, height - 1.2 * inch, f"Fecha: {sale.created_at.strftime('%d/%m/%Y')}")

        # Customer Info
        p.setFont("Helvetica-Bold", 11)
        p.drawString(1 * inch, height - 2.2 * inch, "CLIENTE:")
        p.setFont("Helvetica", 10)
        customer = sale.customer
        if customer:
            p.drawString(1 * inch, height - 2.4 * inch, f"Nombre: {customer.name}")
            p.drawString(1 * inch, height - 2.55 * inch, f"RIF/CI: {customer.tax_id}")
            if customer.address:
                p.drawString(1 * inch, height - 2.7 * inch, f"Dirección: {customer.address}")
        else:
            p.drawString(1 * inch, height - 2.4 * inch, "Consumidor Final")

        # Table Header
        p.setStrokeColor(brand_color)
        p.line(1 * inch, height - 3.1 * inch, 7.5 * inch, height - 3.1 * inch)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(1 * inch, height - 3.25 * inch, "Descripción")
        p.drawString(4.5 * inch, height - 3.25 * inch, "Cant")
        p.drawString(5.5 * inch, height - 3.25 * inch, "Precio Unit. (Bs.)")
        p.drawString(6.8 * inch, height - 3.25 * inch, "Total (Bs.)")
        p.line(1 * inch, height - 3.35 * inch, 7.5 * inch, height - 3.35 * inch)

        # Table Content
        y = height - 3.55 * inch
        p.setFont("Helvetica", 10)
        for detail in sale.details:
            product_name = getattr(detail.product, 'name', f"Producto {detail.product_id}")
            p.drawString(1 * inch, y, product_name[:40])
            p.drawRightString(4.8 * inch, y, str(detail.quantity))
            p.drawRightString(6.3 * inch, y, f"{detail.unit_price:,.2f} Bs.")
            p.drawRightString(7.5 * inch, y, f"{detail.subtotal:,.2f} Bs.")
            y -= 0.25 * inch
            
            if y < 1.5 * inch:
                p.showPage()
                y = height - 1 * inch
                p.setFont("Helvetica", 10)

        # Totals
        y -= 0.2 * inch
        p.setStrokeColor(colors.lightgrey)
        p.line(5 * inch, y, 7.5 * inch, y)
        y -= 0.25 * inch
        p.setFont("Helvetica", 10)
        p.drawString(5 * inch, y, "Subtotal:")
        p.drawRightString(7.5 * inch, y, f"{sale.subtotal:,.2f} Bs.")
        
        # Venezuelan Fiscal Taxes Separation
        standard_iva = sale.subtotal * 0.16
        igtf_total = sale.tax_total - standard_iva if sale.currency == "USD" else 0.0
        
        y -= 0.2 * inch
        p.drawString(5 * inch, y, "IVA (16%):")
        p.drawRightString(7.5 * inch, y, f"{standard_iva:,.2f} Bs.")
        
        if igtf_total > 0.01:
            y -= 0.2 * inch
            p.drawString(5 * inch, y, "IGTF (3%):")
            p.drawRightString(7.5 * inch, y, f"{igtf_total:,.2f} Bs.")
        
        y -= 0.4 * inch
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(5 * inch, y, "TOTAL:")
        p.drawRightString(7.5 * inch, y, f"{sale.total:,.2f} Bs.")

        # Show equivalence in USD if transaction was in USD or exchange rate is set
        if sale.exchange_rate and sale.exchange_rate > 1:
            y -= 0.22 * inch
            p.setFont("Helvetica-Oblique", 9)
            p.setFillColor(colors.black)
            p.drawString(5 * inch, y, f"Tasa BCV del día:")
            p.drawRightString(7.5 * inch, y, f"{sale.exchange_rate:,.2f} Bs/$")
            
            y -= 0.18 * inch
            total_usd = sale.total / sale.exchange_rate
            p.drawString(5 * inch, y, f"Total Ref. USD:")
            p.drawRightString(7.5 * inch, y, f"${total_usd:,.2f}")

        # Footer
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Oblique", 8)
        p.drawCentredString(width / 2, 0.7 * inch, "¡Gracias por su compra!")
        p.drawCentredString(width / 2, 0.5 * inch, "Generado por APEX ERP - Sistema Multi-Tenant")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_thermal_ticket(sale: Sale, width_mm: int = 80) -> io.BytesIO:
        """
        Genera el Ticket Térmico de Venta para impresoras POS de 80mm o 58mm.
        Incluye desglose bimonetario (Bs / USD), IGTF 3%, y datos fiscales SENIAT.
        """
        from reportlab.lib.units import mm
        from decimal import Decimal

        buffer = io.BytesIO()
        width = width_mm * mm
        # Altura dinámica: ~140mm base + 8mm por cada renglón
        num_items = len(sale.details) if sale.details else 1
        height = max(180 * mm, (130 + num_items * 8) * mm)

        p = canvas.Canvas(buffer, pagesize=(width, height))
        y = height - 8 * mm

        # ── ENCABEZADO FISCAL (Centrado) ──────────────────────────────────────
        tenant = sale.tenant
        company_name = tenant.name if tenant else "EMPRESA"
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width / 2, y, company_name[:28].upper())
        y -= 4 * mm

        p.setFont("Helvetica", 7.5)
        if tenant and tenant.tax_id:
            p.drawCentredString(width / 2, y, f"RIF: {tenant.tax_id.upper()}")
            y -= 3.5 * mm

        if tenant and tenant.address:
            addr = tenant.address[:40]
            p.drawCentredString(width / 2, y, addr)
            y -= 3.5 * mm

        if tenant and tenant.phone:
            p.drawCentredString(width / 2, y, f"TELF: {tenant.phone}")
            y -= 3.5 * mm

        # Separador punteado
        y -= 1 * mm
        p.setFont("Helvetica", 7)
        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm

        # ── DATOS DEL DOCUMENTO FISCAL ────────────────────────────────────────
        p.setFont("Helvetica-Bold", 8)
        p.drawString(4 * mm, y, "DOCUMENTO NO FISCAL / TICKET")
        p.drawRightString(width - 4 * mm, y, f"#{str(sale.id).zfill(6)}")
        y -= 3.5 * mm

        if sale.control_number:
            p.setFont("Helvetica", 7)
            p.drawString(4 * mm, y, f"N° Control: {sale.control_number}")
            y -= 3.5 * mm

        date_str = sale.created_at.strftime('%d/%m/%Y %H:%M') if sale.created_at else ""
        p.setFont("Helvetica", 7)
        p.drawString(4 * mm, y, f"Fecha: {date_str}")
        y -= 3.5 * mm

        # Datos del Cliente
        customer = sale.customer
        if customer:
            p.drawString(4 * mm, y, f"Cliente: {customer.name[:25]}")
            y -= 3 * mm
            p.drawString(4 * mm, y, f"CI/RIF: {customer.tax_id or 'V-999999999'}")
            y -= 3.5 * mm
        else:
            p.drawString(4 * mm, y, "Cliente: CONSUMIDOR FINAL")
            y -= 3.5 * mm

        # Separador
        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm

        # ── TABLA DE PRODUCTOS / SERVICIOS ────────────────────────────────────
        p.setFont("Helvetica-Bold", 7)
        p.drawString(4 * mm, y, "DESCRIPCION")
        p.drawRightString(width - 4 * mm, y, "TOTAL")
        y -= 3.5 * mm

        p.setFont("Helvetica", 7)
        rate = float(sale.exchange_rate) if sale.exchange_rate and sale.exchange_rate > 0 else 1.0

        for d in sale.details:
            name = getattr(d.product, 'name', f"Prod {d.product_id}") if d.product else f"Prod {d.product_id}"
            qty = float(d.quantity)
            subt = float(d.subtotal)
            p.drawString(4 * mm, y, f"{name[:22]}")
            p.drawRightString(width - 4 * mm, y, f"{subt:,.2f}")
            y -= 3 * mm
            p.setFont("Helvetica-Oblique", 6.5)
            p.drawString(6 * mm, y, f"{qty:.2f} x {float(d.unit_price):,.2f}")
            p.setFont("Helvetica", 7)
            y -= 3.5 * mm

        # Separador
        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm

        # ── TOTALES Y TRIBUTOS VENEZOLANOS (SENIAT) ───────────────────────────
        subt_f = float(sale.subtotal)
        tax_f = float(sale.tax_total)
        igtf_f = float(sale.igtf_amount) if sale.igtf_amount else 0.0
        tot_f = float(sale.total)

        p.setFont("Helvetica", 7)
        p.drawString(10 * mm, y, "Subtotal:")
        p.drawRightString(width - 4 * mm, y, f"{subt_f:,.2f}")
        y -= 3 * mm

        p.drawString(10 * mm, y, "IVA (16%):")
        p.drawRightString(width - 4 * mm, y, f"{tax_f:,.2f}")
        y -= 3 * mm

        if igtf_f > 0:
            p.drawString(10 * mm, y, "IGTF Divisas (3%):")
            p.drawRightString(width - 4 * mm, y, f"{igtf_f:,.2f}")
            y -= 3 * mm

        # Total Destacado
        y -= 1 * mm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(4 * mm, y, "TOTAL A PAGAR:")
        p.drawRightString(width - 4 * mm, y, f"{tot_f:,.2f} {sale.currency or 'USD'}")
        y -= 4 * mm

        # Equivalencia Bimonetaria
        if sale.currency == 'USD' and rate > 1:
            tot_ves = tot_f * rate
            p.setFont("Helvetica", 7.5)
            p.drawString(4 * mm, y, f"Equiv. en Bolívares:")
            p.drawRightString(width - 4 * mm, y, f"Bs. {tot_ves:,.2f}")
            y -= 3.5 * mm
            p.setFont("Helvetica-Oblique", 6.5)
            p.drawString(4 * mm, y, f"Tasa BCV: {rate:,.2f} Bs/$")
            y -= 4 * mm
        elif sale.currency == 'VES' and rate > 1:
            tot_usd = tot_f / rate
            p.setFont("Helvetica", 7.5)
            p.drawString(4 * mm, y, f"Ref. en Dólares:")
            p.drawRightString(width - 4 * mm, y, f"${tot_usd:,.2f} USD")
            y -= 3.5 * mm
            p.setFont("Helvetica-Oblique", 6.5)
            p.drawString(4 * mm, y, f"Tasa BCV: {rate:,.2f} Bs/$")
            y -= 4 * mm

        # ── PIE DE TICKET ─────────────────────────────────────────────────────
        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm
        p.setFont("Helvetica-Oblique", 6.5)
        p.drawCentredString(width / 2, y, "CONSERVE ESTE TICKET COMO COMPROBANTE")
        y -= 3 * mm
        p.drawCentredString(width / 2, y, "¡Gracias por su compra!")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_withholding_voucher(purchase, tenant) -> io.BytesIO:
        """
        Genera el Comprobante de Retención de IVA oficial exigido por el SENIAT
        conforme a la Providencia Administrativa SNAT/2015/0049.
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        brand_color = colors.HexColor(tenant.primary_color if tenant and tenant.primary_color else "#1e3a8a")

        # ── TÍTULO Y LEYENDA LEGAL SENIAT ─────────────────────────────────────
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width / 2, height - 0.6 * inch, "COMPROBANTE DE RETENCIÓN DEL IMPUESTO AL VALOR AGREGADO (I.V.A.)")
        
        p.setFillColor(colors.HexColor("#4b5563"))
        p.setFont("Helvetica", 7.5)
        p.drawCentredString(
            width / 2, height - 0.75 * inch,
            "(Ley IVA - Art. 11 / Providencia Administrativa SENIAT N° SNAT/2015/0049)"
        )

        # ── NÚMERO DE COMPROBANTE Y FECHA (14 DÍGITOS OFICIAL) ────────────────
        created_dt = purchase.created_at
        voucher_number = f"{created_dt.strftime('%Y%m')}{purchase.id:08d}"
        
        # Caja de información del comprobante
        p.setStrokeColor(colors.HexColor("#cbd5e1"))
        p.setFillColor(colors.HexColor("#f8fafc"))
        p.rect(width - 3.2 * inch, height - 1.45 * inch, 2.7 * inch, 0.55 * inch, fill=1, stroke=1)
        
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(width - 3.1 * inch, height - 1.05 * inch, "N° Comprobante:")
        p.setFont("Helvetica", 8)
        p.drawString(width - 1.9 * inch, height - 1.05 * inch, voucher_number)

        p.setFont("Helvetica-Bold", 8)
        p.drawString(width - 3.1 * inch, height - 1.25 * inch, "Fecha Emisión:")
        p.setFont("Helvetica", 8)
        p.drawString(width - 1.9 * inch, height - 1.25 * inch, created_dt.strftime("%d/%m/%Y"))

        p.setFont("Helvetica-Bold", 8)
        p.drawString(width - 3.1 * inch, height - 1.40 * inch, "Período Fiscal:")
        p.setFont("Helvetica", 8)
        p.drawString(width - 1.9 * inch, height - 1.40 * inch, f"{created_dt.strftime('%m/%Y')}")

        # ── DATOS DEL AGENTE DE RETENCIÓN (EMPRESA) ───────────────────────────
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(0.5 * inch, height - 1.0 * inch, tenant.name if tenant else "EMPRESA AGENTE DE RETENCIÓN")
        
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        p.drawString(0.5 * inch, height - 1.15 * inch, f"R.I.F.: {tenant.tax_id if tenant and tenant.tax_id else 'J-00000000-0'}")
        p.drawString(0.5 * inch, height - 1.30 * inch, f"Dirección: {tenant.address if tenant and tenant.address else 'Venezuela'}")
        if tenant and tenant.phone:
            p.drawString(0.5 * inch, height - 1.45 * inch, f"Teléfono: {tenant.phone}")

        # ── DATOS DEL SUJETO RETENIDO (PROVEEDOR) ─────────────────────────────
        y_box = height - 2.15 * inch
        p.setFillColor(colors.HexColor("#f1f5f9"))
        p.rect(0.5 * inch, y_box, width - 1.0 * inch, 0.55 * inch, fill=1, stroke=1)
        
        supplier = purchase.supplier
        p.setFillColor(colors.HexColor("#0f172a"))
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(0.65 * inch, y_box + 0.38 * inch, "DATOS DEL PROVEEDOR (SUJETO RETENIDO):")
        
        p.setFont("Helvetica", 8)
        p.drawString(0.65 * inch, y_box + 0.22 * inch, f"Razón Social: {supplier.name if supplier else 'Proveedor Desconocido'}")
        p.drawString(4.5 * inch, y_box + 0.22 * inch, f"R.I.F.: {supplier.tax_id if supplier and supplier.tax_id else 'J-00000000-0'}")
        p.drawString(0.65 * inch, y_box + 0.08 * inch, f"Dirección: {supplier.address if supplier and supplier.address else 'N/A'}")

        # ── TABLA DE DETALLE DE LA RETENCIÓN (SENIAT) ─────────────────────────
        y_table = height - 2.45 * inch
        p.setFillColor(brand_color)
        p.rect(0.5 * inch, y_table, width - 1.0 * inch, 0.22 * inch, fill=1, stroke=0)
        
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 6.5)
        p.drawString(0.55 * inch, y_table + 0.06 * inch, "Oper.")
        p.drawString(0.85 * inch, y_table + 0.06 * inch, "Fecha")
        p.drawString(1.45 * inch, y_table + 0.06 * inch, "N° Factura")
        p.drawString(2.30 * inch, y_table + 0.06 * inch, "N° Control")
        p.drawString(3.15 * inch, y_table + 0.06 * inch, "Total Factura")
        p.drawString(4.00 * inch, y_table + 0.06 * inch, "Base Imponible")
        p.drawString(4.85 * inch, y_table + 0.06 * inch, "% Alícuota")
        p.drawString(5.45 * inch, y_table + 0.06 * inch, "Impuesto IVA")
        p.drawString(6.25 * inch, y_table + 0.06 * inch, "% Ret.")
        p.drawString(6.85 * inch, y_table + 0.06 * inch, "IVA Retenido")

        # Fila de datos
        y_row = y_table - 0.25 * inch
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 7.5)
        
        subtotal = float(purchase.subtotal or 0.0)
        tax_total = float(purchase.tax_total or 0.0)
        total = float(purchase.total or 0.0)
        iva_withholding = float(purchase.iva_withholding or 0.0)
        
        # Calcular porcentaje de retención estimado (75% o 100%)
        ret_rate = 75
        if tax_total > 0 and iva_withholding > 0:
            ret_rate = round((iva_withholding / tax_total) * 100)

        p.drawString(0.60 * inch, y_row, "01")
        p.drawString(0.85 * inch, y_row, created_dt.strftime("%d/%m/%Y"))
        p.drawString(1.45 * inch, y_row, str(purchase.invoice_number or purchase.reference or f"F-{purchase.id}"))
        p.drawString(2.30 * inch, y_row, str(purchase.control_number or f"00-{purchase.id:06d}"))
        p.drawString(3.15 * inch, y_row, f"{total:,.2f}")
        p.drawString(4.00 * inch, y_row, f"{subtotal:,.2f}")
        p.drawString(4.95 * inch, y_row, "16%")
        p.drawString(5.45 * inch, y_row, f"{tax_total:,.2f}")
        p.drawString(6.30 * inch, y_row, f"{ret_rate}%")
        p.setFont("Helvetica-Bold", 7.5)
        p.drawString(6.85 * inch, y_row, f"{iva_withholding:,.2f}")

        # Línea separadora
        p.setStrokeColor(colors.HexColor("#cbd5e1"))
        p.line(0.5 * inch, y_row - 0.08 * inch, width - 0.5 * inch, y_row - 0.08 * inch)

        # ── TOTALES CONSOLIDADOS ───────────────────────────────────────────────
        y_tot = y_row - 0.35 * inch
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(4.00 * inch, y_tot, "TOTAL IMPUESTO RETENIDO:")
        p.setFillColor(brand_color)
        p.drawString(6.75 * inch, y_tot, f"{iva_withholding:,.2f} {purchase.currency or 'USD'}")

        # ── SECCIÓN DE FIRMAS Y SELLOS LEGALES ─────────────────────────────────
        y_sign = 1.6 * inch
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.8)
        
        # Firma Agente
        p.line(1.0 * inch, y_sign, 3.5 * inch, y_sign)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(2.25 * inch, y_sign - 0.15 * inch, "AGENTE DE RETENCIÓN")
        p.setFont("Helvetica", 7)
        p.drawCentredString(2.25 * inch, y_sign - 0.28 * inch, "Firma y Sello Húmedo")

        # Firma Proveedor
        p.line(width - 3.5 * inch, y_sign, width - 1.0 * inch, y_sign)
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(width - 2.25 * inch, y_sign - 0.15 * inch, "SUJETO RETENIDO (PROVEEDOR)")
        p.setFont("Helvetica", 7)
        p.drawCentredString(width - 2.25 * inch, y_sign - 0.28 * inch, "Firma, Cédula / Fecha Recepción")

        # Footer informativo
        p.setFont("Helvetica-Oblique", 7)
        p.setFillColor(colors.HexColor("#64748b"))
        p.drawCentredString(
            width / 2, 0.6 * inch,
            "Este documento constituye un comprobante formal de retención de I.V.A. válido a efectos tributarios ante el SENIAT."
        )

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_payroll_receipt(receipt, employee, period, tenant) -> io.BytesIO:
        """
        Genera el Recibo de Pago de Nómina formal según las normativas de la LOTTT de Venezuela.
        Incluye asignaciones, deducciones de ley (SSO, RPE, FAOV), Cestaticket y firmas.
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Color corporativo
        primary_hex = tenant.primary_color if tenant and tenant.primary_color else "#2563eb"
        try:
            brand_color = colors.HexColor(primary_hex)
        except Exception:
            brand_color = colors.HexColor("#2563eb")

        # ── CABECERA / MEMBRETE ──────────────────────────────────────────────
        y = height - 0.7 * inch
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(brand_color)
        company_name = tenant.name if tenant else "EMPRESA"
        p.drawString(0.6 * inch, y, company_name.upper())

        p.setFont("Helvetica", 8)
        p.setFillColor(colors.black)
        y -= 0.16 * inch
        if tenant and tenant.tax_id:
            p.drawString(0.6 * inch, y, f"RIF: {tenant.tax_id.upper()}")
            y -= 0.14 * inch
        if tenant and tenant.address:
            p.drawString(0.6 * inch, y, f"Dirección: {tenant.address}")
            y -= 0.14 * inch

        # Cuadro de Identificación del Recibo
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 12)
        p.drawRightString(width - 0.6 * inch, height - 0.7 * inch, "RECIBO DE PAGO DE NÓMINA")
        p.setFont("Helvetica-Bold", 9)
        p.setFillColor(colors.black)
        p.drawRightString(width - 0.6 * inch, height - 0.88 * inch, f"N° RECIBO: {receipt.receipt_number}")
        p.setFont("Helvetica", 8)
        p.drawRightString(width - 0.6 * inch, height - 1.02 * inch, f"Período: {period.code}")
        p.drawRightString(width - 0.6 * inch, height - 1.16 * inch, f"Desde: {period.start_date.strftime('%d/%m/%Y')}  Hasta: {period.end_date.strftime('%d/%m/%Y')}")
        p.drawRightString(width - 0.6 * inch, height - 1.30 * inch, f"Frecuencia: {period.period_type} | Tasa BCV: {float(receipt.exchange_rate):,.4f} Bs/$")

        # Línea divisoria
        y_div = height - 1.45 * inch
        p.setStrokeColor(brand_color)
        p.setLineWidth(1.5)
        p.line(0.6 * inch, y_div, width - 0.6 * inch, y_div)

        # ── DATOS DEL TRABAJADOR ──────────────────────────────────────────────
        y_emp = y_div - 0.22 * inch
        p.setFillColor(colors.HexColor("#f8fafc"))
        p.rect(0.6 * inch, y_emp - 0.55 * inch, width - 1.2 * inch, 0.65 * inch, fill=True, stroke=False)

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(0.75 * inch, y_emp, f"Trabajador: {employee.first_name} {employee.last_name}")
        p.drawString(4.0 * inch, y_emp, f"Cédula / RIF: {employee.national_id} {f'({employee.rif})' if employee.rif else ''}")

        y_emp -= 0.18 * inch
        p.setFont("Helvetica", 8)
        p.drawString(0.75 * inch, y_emp, f"Cargo: {employee.job_title} | Depto: {employee.department or 'General'}")
        p.drawString(4.0 * inch, y_emp, f"Fecha Ingreso: {employee.hire_date.strftime('%d/%m/%Y')}")

        y_emp -= 0.18 * inch
        bank_info = f"{employee.bank_name or 'Banco'}: {employee.bank_account or 'Sin registrar'}"
        p.drawString(0.75 * inch, y_emp, f"Cuenta Nómina: {bank_info}")
        p.drawString(4.0 * inch, y_emp, f"Sueldo Base Mensual: ${float(employee.salary_usd):,.2f} USD ({float(employee.salary_ves):,.2f} Bs.)")

        # ── TABLA DE ASIGNACIONES Y DEDUCCIONES ────────────────────────────────
        y_table_hdr = y_emp - 0.40 * inch
        col_w = (width - 1.3 * inch) / 2

        # Cabecera Asignaciones
        p.setFillColor(brand_color)
        p.rect(0.6 * inch, y_table_hdr, col_w, 0.22 * inch, fill=True, stroke=False)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(0.75 * inch, y_table_hdr + 0.06 * inch, "ASIGNACIONES (HABERES)")
        p.drawRightString(0.6 * inch + col_w - 0.15 * inch, y_table_hdr + 0.06 * inch, "MONTO BS.")

        # Cabecera Deducciones
        col2_x = 0.6 * inch + col_w + 0.1 * inch
        p.setFillColor(colors.HexColor("#dc2626")) # Rojo deducciones
        p.rect(col2_x, y_table_hdr, col_w, 0.22 * inch, fill=True, stroke=False)
        p.setFillColor(colors.white)
        p.drawString(col2_x + 0.15 * inch, y_table_hdr + 0.06 * inch, "DEDUCCIONES DE LEY")
        p.drawRightString(col2_x + col_w - 0.15 * inch, y_table_hdr + 0.06 * inch, "MONTO BS.")

        # Contenido Asignaciones
        y_row = y_table_hdr - 0.22 * inch
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)

        # 1. Salario Base Quincenal
        base_sal = float(receipt.base_salary_ves)
        p.drawString(0.75 * inch, y_row, "Salario Base Quincenal")
        p.drawRightString(0.6 * inch + col_w - 0.15 * inch, y_row, f"{base_sal:,.2f}")

        # 1. Deducción SSO 4%
        sso = float(receipt.sso_deduction_ves)
        p.drawString(col2_x + 0.15 * inch, y_row, "Seguro Social Obligatorio (S.S.O. 4%)")
        p.drawRightString(col2_x + col_w - 0.15 * inch, y_row, f"{sso:,.2f}")

        y_row -= 0.18 * inch
        # 2. Cestaticket
        cesta = float(receipt.cestaticket_ves)
        p.drawString(0.75 * inch, y_row, "Cestaticket Socialista (Decreto)")
        p.drawRightString(0.6 * inch + col_w - 0.15 * inch, y_row, f"{cesta:,.2f}")

        # 2. Deducción RPE 0.5%
        rpe = float(receipt.rpe_deduction_ves)
        p.drawString(col2_x + 0.15 * inch, y_row, "Régimen Prestacional de Empleo (0.5%)")
        p.drawRightString(col2_x + col_w - 0.15 * inch, y_row, f"{rpe:,.2f}")

        y_row -= 0.18 * inch
        # 3. Otros Bonos
        bonos = float(receipt.other_bonuses_ves)
        if bonos > 0:
            p.drawString(0.75 * inch, y_row, "Bonos / Compensaciones")
            p.drawRightString(0.6 * inch + col_w - 0.15 * inch, y_row, f"{bonos:,.2f}")

        # 3. Deducción FAOV 1%
        faov = float(receipt.faov_deduction_ves)
        p.drawString(col2_x + 0.15 * inch, y_row, "Fondo de Ahorro Habitacional (1%)")
        p.drawRightString(col2_x + col_w - 0.15 * inch, y_row, f"{faov:,.2f}")

        y_row -= 0.18 * inch
        # 4. Otras Deducciones
        other_ded = float(receipt.other_deductions_ves)
        if other_ded > 0:
            p.drawString(col2_x + 0.15 * inch, y_row, "Otras Deducciones")
            p.drawRightString(col2_x + col_w - 0.15 * inch, y_row, f"{other_ded:,.2f}")

        # Líneas de subtotal
        y_subtot = y_row - 0.25 * inch
        p.setStrokeColor(colors.HexColor("#e2e8f0"))
        p.line(0.6 * inch, y_subtot + 0.12 * inch, 0.6 * inch + col_w, y_subtot + 0.12 * inch)
        p.line(col2_x, y_subtot + 0.12 * inch, col2_x + col_w, y_subtot + 0.12 * inch)

        tot_earn = float(receipt.total_earnings_ves)
        tot_ded = float(receipt.total_deductions_ves)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(0.75 * inch, y_subtot, "TOTAL ASIGNACIONES:")
        p.drawRightString(0.6 * inch + col_w - 0.15 * inch, y_subtot, f"{tot_earn:,.2f} Bs.")

        p.drawString(col2_x + 0.15 * inch, y_subtot, "TOTAL DEDUCCIONES:")
        p.drawRightString(col2_x + col_w - 0.15 * inch, y_subtot, f"{tot_ded:,.2f} Bs.")

        # ── TOTAL NETO A COBRAR (DESTACADO) ───────────────────────────────────
        y_net = y_subtot - 0.65 * inch
        net_ves = float(receipt.net_amount_ves)
        net_usd = float(receipt.net_amount_usd)

        p.setFillColor(colors.HexColor("#10b981")) # Verde Éxito
        p.roundRect(0.6 * inch, y_net, width - 1.2 * inch, 0.50 * inch, 6, fill=True, stroke=False)

        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(0.9 * inch, y_net + 0.18 * inch, "NETO A COBRAR POR EL TRABAJADOR:")
        p.drawRightString(width - 0.9 * inch, y_net + 0.18 * inch, f"{net_ves:,.2f} Bs.  |  ${net_usd:,.2f} USD")

        # ── SECCIÓN DE FIRMAS Y MANIFESTACIÓN DE CONFORMIDAD ─────────────────
        y_decl = y_net - 0.50 * inch
        p.setFillColor(colors.HexColor("#475569"))
        p.setFont("Helvetica-Oblique", 7.5)
        conformidad = (
            "Declaro haber recibido a mi entera satisfacción la cantidad neta indicada en este recibo, "
            "correspondiente al período señalado, por concepto de salarios y beneficios de ley según la LOTTT."
        )
        p.drawString(0.6 * inch, y_decl, conformidad)

        y_sign = y_decl - 0.70 * inch
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.8)

        # Firma Patrono
        p.line(1.0 * inch, y_sign, 3.2 * inch, y_sign)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(2.1 * inch, y_sign - 0.14 * inch, "PATRONO / REPRESENTANTE LEGAL")
        p.setFont("Helvetica", 7)
        p.drawCentredString(2.1 * inch, y_sign - 0.26 * inch, "Firma y Sello")

        # Firma y Huella Trabajador
        p.line(width - 3.2 * inch, y_sign, width - 1.0 * inch, y_sign)
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(width - 2.1 * inch, y_sign - 0.14 * inch, "TRABAJADOR(A)")
        p.setFont("Helvetica", 7)
        p.drawCentredString(width - 2.1 * inch, y_sign - 0.26 * inch, "Firma y Huella Dactilar")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

