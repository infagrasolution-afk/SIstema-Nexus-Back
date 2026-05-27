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
                p.drawString(1 * inch, y_header, sale.tenant.name if sale.tenant else "NEXUS ERP")
                y_header -= 0.3 * inch
        else:
            p.setFont("Helvetica-Bold", 20)
            p.setFillColor(brand_color)
            p.drawString(1 * inch, y_header, sale.tenant.name if sale.tenant else "NEXUS ERP")
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
        p.drawString(5.5 * inch, height - 3.25 * inch, "Precio Unit.")
        p.drawString(6.8 * inch, height - 3.25 * inch, "Total")
        p.line(1 * inch, height - 3.35 * inch, 7.5 * inch, height - 3.35 * inch)

        # Table Content
        y = height - 3.55 * inch
        p.setFont("Helvetica", 10)
        for detail in sale.details:
            product_name = getattr(detail.product, 'name', f"Producto {detail.product_id}")
            p.drawString(1 * inch, y, product_name[:40])
            p.drawRightString(4.8 * inch, y, str(detail.quantity))
            p.drawRightString(6.3 * inch, y, f"${detail.unit_price:,.2f}")
            p.drawRightString(7.5 * inch, y, f"${detail.subtotal:,.2f}")
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
        p.drawRightString(7.5 * inch, y, f"${sale.subtotal:,.2f}")
        
        y -= 0.2 * inch
        p.drawString(5 * inch, y, "IVA (16%):")
        p.drawRightString(7.5 * inch, y, f"${sale.tax_total:,.2f}")
        
        y -= 0.4 * inch
        p.setFillColor(brand_color)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(5 * inch, y, "TOTAL:")
        p.drawRightString(7.5 * inch, y, f"${sale.total:,.2f}")

        # Footer
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Oblique", 8)
        p.drawCentredString(width / 2, 0.7 * inch, "¡Gracias por su compra!")
        p.drawCentredString(width / 2, 0.5 * inch, "Generado por NEXUS ERP - Sistema Multi-Tenant")

        p.showPage()
        p.save()
        buffer.seek(0)
        return buffer
