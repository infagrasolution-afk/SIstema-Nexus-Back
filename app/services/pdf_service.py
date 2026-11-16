import io
import base64
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from app.domain.sales import Sale

class PDFService:
    @staticmethod
    def _draw_tenant_logo(p: canvas.Canvas, tenant_or_url, x: float = 0.6 * inch, y: float = 0.0, max_w: float = 1.3 * inch, max_h: float = 0.75 * inch) -> bool:
        """Dibuja el logo de la empresa soportando tanto Base64 Data-URL como rutas/URLs."""
        if not tenant_or_url:
            return False
        if isinstance(tenant_or_url, str):
            logo_url = tenant_or_url.strip()
        else:
            logo_url = (getattr(tenant_or_url, "logo_url", None) or "").strip()
        if not logo_url:
            return False
        try:
            if logo_url.startswith("data:image"):
                header, encoded = logo_url.split(",", 1)
                img_bytes = base64.b64decode(encoded)
                img_reader = ImageReader(io.BytesIO(img_bytes))
                p.drawImage(img_reader, x, y, width=max_w, height=max_h, preserveAspectRatio=True, anchor='nw', mask='auto')
                return True
            else:
                p.drawImage(logo_url, x, y, width=max_w, height=max_h, preserveAspectRatio=True, anchor='nw', mask='auto')
                return True
        except Exception as e:
            print(f"Notice loading tenant logo for PDF: {e}")
            return False

    @staticmethod
    def generate_invoice(sale: Sale) -> io.BytesIO:
        """
        Genera Factura Fiscal / Digital conforme a las Providencias Administrativas
        del SENIAT en Venezuela (SNAT/2011/00071 y SNAT/2014/0032) y Ley de IGTF.
        Incluye logo de la empresa, RIF, N° de Factura, N° de Control, Base Imponible,
        Exento, IVA (16%), IGTF (3%) y equivalencia bimonetaria a tasa BCV.
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        tenant = sale.tenant
        primary_color_hex = tenant.primary_color if tenant and tenant.primary_color else "#1e3a8a"
        try:
            brand_color = colors.HexColor(primary_color_hex)
        except Exception:
            brand_color = colors.HexColor("#1e3a8a")

        # ── 1. ENCABEZADO EMISOR Y LOGO DE LA EMPRESA ─────────────────────────
        y_top = height - 0.6 * inch
        logo_drawn = PDFService._draw_tenant_logo(p, tenant, 0.6 * inch, height - 1.35 * inch, 1.3 * inch, 0.75 * inch)
        text_x = (2.0 * inch) if logo_drawn else (0.6 * inch)

        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 14)
        company_name = (tenant.name if tenant and tenant.name else "EMPRESA EMISORA").upper()
        p.drawString(text_x, y_top - 0.15 * inch, company_name[:42])

        p.setFillColor(colors.HexColor("#1e293b"))
        p.setFont("Helvetica-Bold", 9)
        rif_str = tenant.tax_id.upper() if tenant and tenant.tax_id else "J-00000000-0"
        p.drawString(text_x, y_top - 0.32 * inch, f"R.I.F.: {rif_str}")

        p.setFont("Helvetica", 8)
        addr_str = tenant.address if tenant and tenant.address else "Domicilio Fiscal: Venezuela"
        p.drawString(text_x, y_top - 0.46 * inch, f"Domicilio Fiscal: {addr_str[:65]}")
        if len(addr_str) > 65:
            p.drawString(text_x, y_top - 0.58 * inch, addr_str[65:130])

        phone_str = tenant.phone if tenant and tenant.phone else "N/A"
        email_str = tenant.email if tenant and tenant.email else ""
        contact_line = f"Teléfono: {phone_str}" + (f"  |  Email: {email_str}" if email_str else "")
        p.drawString(text_x, y_top - 0.72 * inch, contact_line[:75])

        # ── 2. CUADRO FISCAL DE NUMERACIÓN SENIAT (DERECHA) ───────────────────
        box_x = width - 3.05 * inch
        box_y = height - 1.48 * inch
        p.setStrokeColor(brand_color)
        p.setFillColor(colors.HexColor("#f8fafc"))
        p.roundRect(box_x, box_y, 2.45 * inch, 0.92 * inch, 6, fill=1, stroke=1)

        inv_num = sale.fiscal_invoice_number or f"{sale.id:08d}"
        ctrl_num = sale.control_number or f"00-{sale.id:08d}"
        dt_str = sale.created_at.strftime('%d/%m/%Y %H:%M') if sale.created_at else ""

        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(box_x + 1.225 * inch, box_y + 0.72 * inch, "FACTURA")

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(box_x + 0.12 * inch, box_y + 0.52 * inch, "N° DE FACTURA:")
        p.setFillColor(colors.HexColor("#dc2626"))
        p.drawRightString(box_x + 2.33 * inch, box_y + 0.52 * inch, str(inv_num))

        p.setFillColor(colors.black)
        p.drawString(box_x + 0.12 * inch, box_y + 0.36 * inch, "N° DE CONTROL:")
        p.setFont("Helvetica-Bold", 8.5)
        p.drawRightString(box_x + 2.33 * inch, box_y + 0.36 * inch, str(ctrl_num))

        p.setFont("Helvetica", 7.5)
        p.drawString(box_x + 0.12 * inch, box_y + 0.20 * inch, "Fecha y Hora Emisión:")
        p.drawRightString(box_x + 2.33 * inch, box_y + 0.20 * inch, dt_str)

        payment_map = {
            "cash": "Contado / Efectivo",
            "card": "Contado / Punto de Venta",
            "transfer": "Contado / Transferencia / Pago Móvil",
            "credit": "Crédito Comercial",
            "zelle": "Contado / Divisas (Zelle)"
        }
        pay_label = payment_map.get(sale.payment_method or "cash", sale.payment_method or "Contado")
        p.drawString(box_x + 0.12 * inch, box_y + 0.06 * inch, f"Condición: {pay_label[:26]}")

        # ── 3. DATOS DEL CLIENTE / ADQUIRENTE (EXIGIDO POR SENIAT) ────────────
        cust_y = height - 2.25 * inch
        p.setStrokeColor(colors.HexColor("#cbd5e1"))
        p.setFillColor(colors.HexColor("#f1f5f9"))
        p.roundRect(0.6 * inch, cust_y, width - 1.2 * inch, 0.65 * inch, 5, fill=1, stroke=1)

        customer = sale.customer
        cust_name = customer.name if customer and customer.name else "CONSUMIDOR FINAL"
        cust_rif = customer.tax_id if customer and customer.tax_id else "V-00000000-0"
        cust_addr = customer.address if customer and customer.address else "Venezuela"
        cust_phone = customer.phone if customer and customer.phone else "N/A"

        p.setFillColor(colors.HexColor("#0f172a"))
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(0.75 * inch, cust_y + 0.45 * inch, f"NOMBRE O RAZÓN SOCIAL: {cust_name[:52].upper()}")
        p.drawString(5.1 * inch, cust_y + 0.45 * inch, f"R.I.F. / C.I.: {cust_rif.upper()}")

        p.setFont("Helvetica", 8)
        p.drawString(0.75 * inch, cust_y + 0.26 * inch, f"DOMICILIO FISCAL: {cust_addr[:70]}")
        p.drawString(5.1 * inch, cust_y + 0.26 * inch, f"TELÉFONO: {cust_phone}")

        rate = float(sale.exchange_rate) if sale.exchange_rate and float(sale.exchange_rate) > 0 else 1.0
        curr_code = "VES" if sale.currency in ["LOCAL", "VES"] else "USD"
        p.drawString(0.75 * inch, cust_y + 0.08 * inch, f"Moneda de Operación: {curr_code}  |  Tasa Oficial BCV Aplicada: {rate:,.2f} Bs/$")

        # ── 4. TABLA DE ÍTEMS FACTURADOS ──────────────────────────────────────
        tbl_top = cust_y - 0.18 * inch
        p.setFillColor(brand_color)
        p.rect(0.6 * inch, tbl_top - 0.22 * inch, width - 1.2 * inch, 0.22 * inch, fill=1, stroke=0)

        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 7.5)
        hdr_y = tbl_top - 0.15 * inch
        p.drawString(0.68 * inch, hdr_y, "CÓDIGO")
        p.drawString(1.55 * inch, hdr_y, "DESCRIPCIÓN DEL BIEN O SERVICIO")
        p.drawRightString(4.65 * inch, hdr_y, "CANT.")
        p.drawCentredString(5.05 * inch, hdr_y, "ALÍC.")
        p.drawRightString(6.05 * inch, hdr_y, f"P. UNIT ({curr_code})")
        p.drawRightString(6.75 * inch, hdr_y, "DESC.")
        p.drawRightString(7.82 * inch, hdr_y, f"SUBTOTAL ({curr_code})")

        y = tbl_top - 0.38 * inch
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)

        exempt_total = 0.0
        taxable_base = 0.0

        for detail in sale.details:
            prod = detail.product
            sku = getattr(prod, 'sku', f"P-{detail.product_id}") if prod else f"P-{detail.product_id}"
            product_name = getattr(prod, 'name', f"Producto {detail.product_id}") if prod else f"Producto {detail.product_id}"
            is_exempt = bool(getattr(prod, 'tax_exempt', False)) if prod else False
            tax_indicator = "(E)" if is_exempt else "(G 16%)"

            qty = float(detail.quantity or 0)
            u_price = float(detail.unit_price or 0)
            disc_pct = float(getattr(detail, 'discount_percent', 0) or 0)
            line_sub = float(detail.subtotal or (qty * u_price))

            if is_exempt:
                exempt_total += line_sub
            else:
                taxable_base += line_sub

            p.drawString(0.68 * inch, y, str(sku)[:12])
            p.drawString(1.55 * inch, y, str(product_name)[:44])
            p.drawRightString(4.65 * inch, y, f"{qty:,.2f}")
            p.drawCentredString(5.05 * inch, y, tax_indicator)
            p.drawRightString(6.05 * inch, y, f"{u_price:,.2f}")
            p.drawRightString(6.75 * inch, y, f"{disc_pct:.0f}%" if disc_pct > 0 else "—")
            p.drawRightString(7.82 * inch, y, f"{line_sub:,.2f}")

            p.setStrokeColor(colors.HexColor("#e2e8f0"))
            p.line(0.6 * inch, y - 0.06 * inch, width - 0.6 * inch, y - 0.06 * inch)
            y -= 0.22 * inch

            if y < 2.6 * inch:
                p.showPage()
                y = height - 1.0 * inch
                p.setFont("Helvetica", 8)

        # ── 5. DESGLOSE TRIBUTARIO SENIAT Y EQUIVALENCIA BCV ──────────────────
        y_tot = min(y - 0.15 * inch, 2.75 * inch)
        p.setStrokeColor(brand_color)
        p.line(0.6 * inch, y_tot + 0.1 * inch, width - 0.6 * inch, y_tot + 0.1 * inch)

        subtotal_f = float(sale.subtotal or 0.0)
        igtf_f = float(sale.igtf_amount or 0.0)
        raw_tax_total = float(sale.tax_total or 0.0)
        # En SalesService, tax_total almacena IVA + IGTF; separamos IVA puro para claridad SENIAT
        iva_f = max(0.0, raw_tax_total - igtf_f) if raw_tax_total >= igtf_f else (taxable_base * 0.16)
        total_f = float(sale.total or 0.0)

        # Columna Izquierda: Nota legal BCV y SENIAT + Cuadro de Equivalencia en Bolívares
        p.setFillColor(colors.HexColor("#f8fafc"))
        p.setStrokeColor(colors.HexColor("#cbd5e1"))
        p.roundRect(0.6 * inch, y_tot - 1.15 * inch, 3.8 * inch, 1.15 * inch, 5, fill=1, stroke=1)

        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(0.72 * inch, y_tot - 0.18 * inch, "EQUIVALENCIA OFICIAL EN BOLÍVARES (BCV):")

        p.setFillColor(colors.black)
        p.setFont("Helvetica", 7.5)
        if curr_code == "USD":
            sub_bs = subtotal_f * rate
            iva_bs = iva_f * rate
            igtf_bs = igtf_f * rate
            tot_bs = total_f * rate
        else:
            sub_bs = subtotal_f
            iva_bs = iva_f
            igtf_bs = igtf_f
            tot_bs = total_f

        p.drawString(0.72 * inch, y_tot - 0.34 * inch, f"• Base Imponible en Bs.: Bs. {sub_bs:,.2f}")
        p.drawString(0.72 * inch, y_tot - 0.48 * inch, f"• I.V.A. (16%) en Bs.: Bs. {iva_bs:,.2f}")
        if igtf_bs > 0.001:
            p.drawString(0.72 * inch, y_tot - 0.62 * inch, f"• I.G.T.F. (3%) en Bs.: Bs. {igtf_bs:,.2f}")
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(0.72 * inch, y_tot - 0.80 * inch, f"• TOTAL EN BOLÍVARES: Bs. {tot_bs:,.2f} (Tasa BCV: {rate:,.2f} Bs/$)")

        p.setFont("Helvetica-Oblique", 6.5)
        p.setFillColor(colors.HexColor("#475569"))
        p.drawString(0.72 * inch, y_tot - 1.02 * inch, "Art. 25 Ley de IVA / Art. 128 Ley del BCV: Pagos en Bs. a la tasa BCV vigente.")

        # Columna Derecha: Totales del Documento
        col_lbl = 4.65 * inch
        col_val = width - 0.65 * inch
        row_y = y_tot - 0.12 * inch

        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8.5)
        p.drawString(col_lbl, row_y, "Total Ventas Exentas (E):")
        p.drawRightString(col_val, row_y, f"{exempt_total:,.2f} {curr_code}")

        row_y -= 0.18 * inch
        p.drawString(col_lbl, row_y, "Base Imponible (G 16%):")
        p.drawRightString(col_val, row_y, f"{taxable_base:,.2f} {curr_code}")

        row_y -= 0.18 * inch
        p.drawString(col_lbl, row_y, "Impuesto I.V.A. (16%):")
        p.drawRightString(col_val, row_y, f"{iva_f:,.2f} {curr_code}")

        if igtf_f > 0.001:
            row_y -= 0.18 * inch
            p.setFillColor(colors.HexColor("#b45309"))
            p.setFont("Helvetica-Bold", 8.5)
            p.drawString(col_lbl, row_y, "I.G.T.F. (3% Pago en Divisas):")
            p.drawRightString(col_val, row_y, f"{igtf_f:,.2f} {curr_code}")

        row_y -= 0.26 * inch
        p.setFillColor(brand_color)
        p.rect(col_lbl - 0.08 * inch, row_y - 0.06 * inch, (col_val - col_lbl) + 0.14 * inch, 0.26 * inch, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10.5)
        p.drawString(col_lbl, row_y + 0.02 * inch, "TOTAL A PAGAR:")
        p.drawRightString(col_val, row_y + 0.02 * inch, f"{total_f:,.2f} {curr_code}")

        # ── 6. PIE DE IMPRENTA / CONFORMIDAD SENIAT ───────────────────────────
        p.setFillColor(colors.HexColor("#475569"))
        p.setFont("Helvetica", 7)
        p.drawCentredString(
            width / 2, 0.72 * inch,
            f"Documento emitido conforme a las Providencias Administrativas SENIAT SNAT/2011/00071 y SNAT/2014/0032. Control N° {ctrl_num}."
        )
        p.setFont("Helvetica-Oblique", 7)
        p.drawCentredString(width / 2, 0.55 * inch, "¡Gracias por su compra! — Emitido mediante plataforma APEX ERP")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_thermal_ticket(sale: Sale, width_mm: int = 80) -> io.BytesIO:
        """
        Genera el Ticket Térmico de Venta para impresoras POS de 80mm o 58mm.
        Incluye logo de la empresa, desglose bimonetario (Bs / USD), IGTF 3% y datos fiscales SENIAT.
        """
        buffer = io.BytesIO()
        width = width_mm * mm
        num_items = len(sale.details) if sale.details else 1
        height = max(200 * mm, (155 + num_items * 9) * mm)

        p = canvas.Canvas(buffer, pagesize=(width, height))
        y = height - 6 * mm

        tenant = sale.tenant
        # Intentar dibujar logo centrado si existe
        if tenant and getattr(tenant, "logo_url", None):
            logo_w = 26 * mm
            logo_h = 14 * mm
            if PDFService._draw_tenant_logo(p, tenant, (width - logo_w) / 2, y - logo_h, logo_w, logo_h):
                y -= (logo_h + 4 * mm)

        # ── ENCABEZADO FISCAL (Centrado) ──────────────────────────────────────
        company_name = tenant.name if tenant and tenant.name else "EMPRESA"
        p.setFont("Helvetica-Bold", 9.5)
        p.drawCentredString(width / 2, y, company_name[:30].upper())
        y -= 3.8 * mm

        p.setFont("Helvetica-Bold", 7.5)
        if tenant and tenant.tax_id:
            p.drawCentredString(width / 2, y, f"R.I.F.: {tenant.tax_id.upper()}")
            y -= 3.4 * mm

        p.setFont("Helvetica", 7)
        if tenant and tenant.address:
            addr = tenant.address
            p.drawCentredString(width / 2, y, addr[:42])
            y -= 3.2 * mm
            if len(addr) > 42:
                p.drawCentredString(width / 2, y, addr[42:84])
                y -= 3.2 * mm

        if tenant and tenant.phone:
            p.drawCentredString(width / 2, y, f"TELF: {tenant.phone}")
            y -= 3.4 * mm

        # Separador punteado
        p.setFont("Helvetica", 7)
        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm

        # ── DATOS DEL DOCUMENTO Y CLIENTE (SENIAT) ────────────────────────────
        inv_num = sale.fiscal_invoice_number or f"{sale.id:08d}"
        ctrl_num = sale.control_number or f"00-{sale.id:08d}"
        p.setFont("Helvetica-Bold", 8)
        p.drawString(3.5 * mm, y, f"FACTURA N°: {inv_num}")
        y -= 3.4 * mm

        p.setFont("Helvetica", 7)
        p.drawString(3.5 * mm, y, f"N° CONTROL: {ctrl_num}")
        y -= 3.4 * mm

        date_str = sale.created_at.strftime('%d/%m/%Y %H:%M') if sale.created_at else ""
        p.drawString(3.5 * mm, y, f"FECHA: {date_str}")
        y -= 3.4 * mm

        customer = sale.customer
        if customer:
            p.drawString(3.5 * mm, y, f"CLIENTE: {customer.name[:28].upper()}")
            y -= 3.2 * mm
            p.drawString(3.5 * mm, y, f"RIF/CI: {customer.tax_id or 'V-00000000-0'}")
            y -= 3.2 * mm
            if customer.address:
                p.drawString(3.5 * mm, y, f"DIR: {customer.address[:34]}")
                y -= 3.2 * mm
        else:
            p.drawString(3.5 * mm, y, "CLIENTE: CONSUMIDOR FINAL")
            y -= 3.4 * mm

        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm

        # ── TABLA DE PRODUCTOS / SERVICIOS ────────────────────────────────────
        p.setFont("Helvetica-Bold", 7)
        p.drawString(3.5 * mm, y, "CANT x PRECIO / DESCRIPCIÓN")
        p.drawRightString(width - 3.5 * mm, y, "MONTO")
        y -= 3.5 * mm

        p.setFont("Helvetica", 7)
        rate = float(sale.exchange_rate) if sale.exchange_rate and float(sale.exchange_rate) > 0 else 1.0
        curr_code = "VES" if sale.currency in ["LOCAL", "VES"] else "USD"

        exempt_total = 0.0
        taxable_base = 0.0

        for d in sale.details:
            prod = d.product
            name = getattr(prod, 'name', f"Prod {d.product_id}") if prod else f"Prod {d.product_id}"
            is_exempt = bool(getattr(prod, 'tax_exempt', False)) if prod else False
            flag = "(E)" if is_exempt else "(G)"
            qty = float(d.quantity or 0)
            subt = float(d.subtotal or 0)
            if is_exempt:
                exempt_total += subt
            else:
                taxable_base += subt

            p.drawString(3.5 * mm, y, f"{name[:24]} {flag}")
            p.drawRightString(width - 3.5 * mm, y, f"{subt:,.2f}")
            y -= 3 * mm
            p.setFont("Helvetica-Oblique", 6.5)
            p.drawString(5 * mm, y, f"{qty:.2f} x {float(d.unit_price):,.2f} {curr_code}")
            p.setFont("Helvetica", 7)
            y -= 3.4 * mm

        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm

        # ── TOTALES Y TRIBUTOS VENEZOLANOS (SENIAT) ───────────────────────────
        subt_f = float(sale.subtotal or 0.0)
        igtf_f = float(sale.igtf_amount or 0.0)
        raw_tax = float(sale.tax_total or 0.0)
        iva_f = max(0.0, raw_tax - igtf_f) if raw_tax >= igtf_f else (taxable_base * 0.16)
        tot_f = float(sale.total or 0.0)

        p.setFont("Helvetica", 7)
        if exempt_total > 0:
            p.drawString(6 * mm, y, "Exento (E):")
            p.drawRightString(width - 3.5 * mm, y, f"{exempt_total:,.2f}")
            y -= 3.2 * mm

        p.drawString(6 * mm, y, "Base Imponible (G 16%):")
        p.drawRightString(width - 3.5 * mm, y, f"{subt_f:,.2f}")
        y -= 3.2 * mm

        p.drawString(6 * mm, y, "I.V.A. (16%):")
        p.drawRightString(width - 3.5 * mm, y, f"{iva_f:,.2f}")
        y -= 3.2 * mm

        if igtf_f > 0.001:
            p.drawString(6 * mm, y, "I.G.T.F. Divisas (3%):")
            p.drawRightString(width - 3.5 * mm, y, f"{igtf_f:,.2f}")
            y -= 3.2 * mm

        y -= 1 * mm
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(3.5 * mm, y, "TOTAL A PAGAR:")
        p.drawRightString(width - 3.5 * mm, y, f"{tot_f:,.2f} {curr_code}")
        y -= 3.8 * mm

        # Equivalencia Bimonetaria Oficial BCV
        if curr_code == 'USD' and rate > 1:
            tot_ves = tot_f * rate
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(3.5 * mm, y, "EQUIV. EN BOLÍVARES:")
            p.drawRightString(width - 3.5 * mm, y, f"Bs. {tot_ves:,.2f}")
            y -= 3.2 * mm
            p.setFont("Helvetica-Oblique", 6.5)
            p.drawString(3.5 * mm, y, f"Tasa Oficial BCV: {rate:,.2f} Bs/$")
            y -= 3.8 * mm
        elif curr_code == 'VES' and rate > 1:
            tot_usd = tot_f / rate
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(3.5 * mm, y, "REF. EN DÓLARES:")
            p.drawRightString(width - 3.5 * mm, y, f"${tot_usd:,.2f} USD")
            y -= 3.2 * mm
            p.setFont("Helvetica-Oblique", 6.5)
            p.drawString(3.5 * mm, y, f"Tasa Oficial BCV: {rate:,.2f} Bs/$")
            y -= 3.8 * mm

        # ── PIE DE TICKET ─────────────────────────────────────────────────────
        p.drawCentredString(width / 2, y, "--------------------------------------------------")
        y -= 3.5 * mm
        p.setFont("Helvetica-Oblique", 6.5)
        p.drawCentredString(width / 2, y, "CONSERVE ESTE COMPROBANTE FISCAL")
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

        # ── DATOS DEL AGENTE DE RETENCIÓN (EMPRESA) + LOGO ────────────────────
        text_x = 0.5 * inch
        if tenant and getattr(tenant, "logo_url", None):
            drawn = PDFService._draw_tenant_logo(
                p, tenant.logo_url,
                x=0.5 * inch, y=height - 1.55 * inch,
                max_w=1.25 * inch, max_h=0.65 * inch
            )
            if drawn:
                text_x = 1.85 * inch

        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(text_x, height - 1.0 * inch, tenant.name if tenant else "EMPRESA AGENTE DE RETENCIÓN")
        
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        p.drawString(text_x, height - 1.15 * inch, f"R.I.F.: {tenant.tax_id if tenant and tenant.tax_id else 'J-00000000-0'}")
        p.drawString(text_x, height - 1.30 * inch, f"Dirección: {tenant.address if tenant and tenant.address else 'Venezuela'}")
        if tenant and tenant.phone:
            p.drawString(text_x, height - 1.45 * inch, f"Teléfono: {tenant.phone}")

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

        # ── CABECERA / MEMBRETE + LOGO ───────────────────────────────────────
        text_x = 0.6 * inch
        if tenant and getattr(tenant, "logo_url", None):
            drawn = PDFService._draw_tenant_logo(
                p, tenant.logo_url,
                x=0.6 * inch, y=height - 1.35 * inch,
                max_w=1.3 * inch, max_h=0.7 * inch
            )
            if drawn:
                text_x = 2.0 * inch

        y = height - 0.7 * inch
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(brand_color)
        company_name = tenant.name if tenant else "EMPRESA"
        p.drawString(text_x, y, company_name.upper())

        p.setFont("Helvetica", 8)
        p.setFillColor(colors.black)
        y -= 0.16 * inch
        if tenant and tenant.tax_id:
            p.drawString(text_x, y, f"RIF: {tenant.tax_id.upper()}")
            y -= 0.14 * inch
        if tenant and tenant.address:
            p.drawString(text_x, y, f"Dirección: {tenant.address}")
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

    @staticmethod
    def generate_purchase_order(purchase, tenant) -> io.BytesIO:
        """
        Genera el documento PDF formal de Orden de Compra con Logo de la Empresa,
        datos fiscales en Venezuela (RIF, Domicilio Fiscal, Proveedor, Detalle e IVA).
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        try:
            brand_color = colors.HexColor(tenant.primary_color if tenant and tenant.primary_color else "#1e3a8a")
        except Exception:
            brand_color = colors.HexColor("#1e3a8a")

        # ── CABECERA Y LOGO EMPRESA ──────────────────────────────────────────
        text_x = 0.55 * inch
        if tenant and getattr(tenant, "logo_url", None):
            drawn = PDFService._draw_tenant_logo(
                p, tenant.logo_url,
                x=0.55 * inch, y=height - 1.45 * inch,
                max_w=1.45 * inch, max_h=0.85 * inch
            )
            if drawn:
                text_x = 2.15 * inch

        y_hdr = height - 0.68 * inch
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 13)
        p.drawString(text_x, y_hdr, (tenant.name if tenant and tenant.name else "EMPRESA S.A.").upper()[:45])

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8.5)
        y_hdr -= 0.16 * inch
        p.drawString(text_x, y_hdr, f"R.I.F.: {tenant.tax_id if tenant and tenant.tax_id else 'J-00000000-0'}")

        p.setFont("Helvetica", 7.5)
        y_hdr -= 0.14 * inch
        p.drawString(text_x, y_hdr, f"Domicilio Fiscal: {(tenant.address if tenant and tenant.address else 'Venezuela')[:65]}")
        if tenant and tenant.phone:
            y_hdr -= 0.13 * inch
            p.drawString(text_x, y_hdr, f"Teléfono: {tenant.phone}  {f'| Email: {tenant.email}' if tenant.email else ''}")

        # ── RECUADRO ORDEN DE COMPRA ─────────────────────────────────────────
        box_w = 2.55 * inch
        box_h = 0.90 * inch
        box_x = width - 0.55 * inch - box_w
        box_y = height - 1.45 * inch
        p.setStrokeColor(brand_color)
        p.setFillColor(colors.HexColor("#f8fafc"))
        p.roundRect(box_x, box_y, box_w, box_h, 5, fill=1, stroke=1)

        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(box_x + box_w / 2, box_y + box_h - 0.20 * inch, "ORDEN DE COMPRA")

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(box_x + 0.12 * inch, box_y + box_h - 0.40 * inch, "N° Orden:")
        p.setFillColor(colors.HexColor("#dc2626"))
        p.drawRightString(box_x + box_w - 0.12 * inch, box_y + box_h - 0.40 * inch, f"OC-{purchase.id:06d}")

        created_dt = purchase.created_at
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 7.5)
        p.drawString(box_x + 0.12 * inch, box_y + box_h - 0.57 * inch, "Fecha Emisión:")
        p.drawRightString(box_x + box_w - 0.12 * inch, box_y + box_h - 0.57 * inch, created_dt.strftime("%d/%m/%Y %H:%M") if created_dt else "N/A")

        p.drawString(box_x + 0.12 * inch, box_y + box_h - 0.73 * inch, "Estado:")
        p.setFont("Helvetica-Bold", 7.5)
        p.drawRightString(box_x + box_w - 0.12 * inch, box_y + box_h - 0.73 * inch, str(purchase.status.value if hasattr(purchase.status, "value") else purchase.status))

        # ── DATOS DEL PROVEEDOR ──────────────────────────────────────────────
        y_sup = height - 2.25 * inch
        p.setStrokeColor(colors.HexColor("#cbd5e1"))
        p.setFillColor(colors.HexColor("#f1f5f9"))
        p.roundRect(0.55 * inch, y_sup, width - 1.10 * inch, 0.65 * inch, 4, fill=1, stroke=1)

        supplier = getattr(purchase, "supplier", None)
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(0.68 * inch, y_sup + 0.47 * inch, "DATOS DEL PROVEEDOR:")

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(0.68 * inch, y_sup + 0.30 * inch, f"Razón Social: {supplier.name if supplier else 'Proveedor General'}")
        p.drawString(4.60 * inch, y_sup + 0.30 * inch, f"R.I.F.: {supplier.tax_id if supplier and supplier.tax_id else 'N/A'}")

        p.setFont("Helvetica", 7.5)
        p.drawString(0.68 * inch, y_sup + 0.13 * inch, f"Dirección: {(supplier.address if supplier and supplier.address else 'Venezuela')[:65]}")
        p.drawString(4.60 * inch, y_sup + 0.13 * inch, f"Condición Pago: {str(purchase.payment_method or 'Contado').upper()} | Ref: {purchase.reference or 'S/R'}")

        # ── TABLA DE ÍTEMS DE LA ORDEN DE COMPRA ─────────────────────────────
        y_tbl = y_sup - 0.32 * inch
        p.setFillColor(brand_color)
        p.rect(0.55 * inch, y_tbl, width - 1.10 * inch, 0.24 * inch, fill=1, stroke=0)

        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(0.65 * inch, y_tbl + 0.07 * inch, "CÓDIGO / SKU")
        p.drawString(1.80 * inch, y_tbl + 0.07 * inch, "DESCRIPCIÓN DEL ARTÍCULO / INSUMO")
        p.drawRightString(5.35 * inch, y_tbl + 0.07 * inch, "CANT.")
        p.drawRightString(6.50 * inch, y_tbl + 0.07 * inch, "COSTO UNIT.")
        p.drawRightString(width - 0.65 * inch, y_tbl + 0.07 * inch, "SUBTOTAL")

        y_row = y_tbl - 0.20 * inch
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        curr_sym = "Bs." if getattr(purchase, "currency", "USD") == "VES" else "$"

        for idx, det in enumerate(getattr(purchase, "details", []) or []):
            if y_row < 2.2 * inch:
                p.showPage()
                y_row = height - 1.0 * inch
                p.setFont("Helvetica", 8)

            if idx % 2 == 1:
                p.setFillColor(colors.HexColor("#f8fafc"))
                p.rect(0.55 * inch, y_row - 0.05 * inch, width - 1.10 * inch, 0.19 * inch, fill=1, stroke=0)
                p.setFillColor(colors.black)

            prod = getattr(det, "product", None)
            sku = prod.sku if prod and getattr(prod, "sku", None) else f"ID-{det.product_id}"
            name = prod.name if prod and getattr(prod, "name", None) else f"Producto #{det.product_id}"
            qty = float(det.quantity or 0)
            cost = float(det.cost_price or 0)
            sub = float(det.subtotal or (qty * cost))

            p.drawString(0.65 * inch, y_row, str(sku)[:16])
            p.drawString(1.80 * inch, y_row, str(name)[:48])
            p.drawRightString(5.35 * inch, y_row, f"{qty:,.2f}")
            p.drawRightString(6.50 * inch, y_row, f"{curr_sym}{cost:,.2f}")
            p.drawRightString(width - 0.65 * inch, y_row, f"{curr_sym}{sub:,.2f}")
            y_row -= 0.20 * inch

        # ── TOTALES DE LA ORDEN DE COMPRA ────────────────────────────────────
        y_tot = min(y_row - 0.15 * inch, 2.55 * inch)
        p.setStrokeColor(colors.HexColor("#cbd5e1"))
        p.line(0.55 * inch, y_tot + 0.15 * inch, width - 0.55 * inch, y_tot + 0.15 * inch)

        subtotal_val = float(purchase.subtotal or 0)
        tax_val = float(purchase.tax_total or 0)
        total_val = float(purchase.total or 0)
        rate_val = float(getattr(purchase, "exchange_rate", 1.0) or 1.0)

        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(4.90 * inch, y_tot, "Base Imponible:")
        p.setFont("Helvetica", 8.5)
        p.drawRightString(width - 0.65 * inch, y_tot, f"{curr_sym}{subtotal_val:,.2f}")

        y_tot -= 0.18 * inch
        p.setFont("Helvetica-Bold", 8.5)
        p.drawString(4.90 * inch, y_tot, "I.V.A. (16%):")
        p.setFont("Helvetica", 8.5)
        p.drawRightString(width - 0.65 * inch, y_tot, f"{curr_sym}{tax_val:,.2f}")

        y_tot -= 0.22 * inch
        p.setFillColor(brand_color)
        p.rect(4.80 * inch, y_tot - 0.06 * inch, width - 5.35 * inch, 0.24 * inch, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 9.5)
        p.drawString(4.90 * inch, y_tot, "TOTAL ORDEN:")
        p.drawRightString(width - 0.65 * inch, y_tot, f"{curr_sym}{total_val:,.2f}")

        if rate_val > 1 and curr_sym == "$":
            y_tot -= 0.18 * inch
            p.setFillColor(colors.HexColor("#334155"))
            p.setFont("Helvetica-Bold", 7.5)
            p.drawRightString(width - 0.65 * inch, y_tot, f"Equivalente Bs. (Tasa BCV {rate_val:,.2f}): Bs. {(total_val * rate_val):,.2f}")

        # ── FIRMAS AUTORIZADAS ───────────────────────────────────────────────
        y_sign = 1.15 * inch
        p.setStrokeColor(colors.black)
        p.setLineWidth(0.8)
        p.line(0.9 * inch, y_sign, 3.2 * inch, y_sign)
        p.line(width - 3.2 * inch, y_sign, width - 0.9 * inch, y_sign)

        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(2.05 * inch, y_sign - 0.15 * inch, "SOLICITADO / COMPRAS")
        p.drawCentredString(width - 2.05 * inch, y_sign - 0.15 * inch, "APROBADO / GERENCIA")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer


