from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from app.api.deps import get_current_user
from app.domain.user import User
import io

router = APIRouter()

MANUAL_TEXT_ES = """# 📘 MANUAL DE USUARIO OFICIAL — APEX ERP

**Desarrollado por:** InfaGraSolution  
**Director de Sistemas / Soporte:** Luis Infante  
**Teléfono / WhatsApp:** 0412-0161906  
**Correo Electrónico:** infagrasolution@gmail.com  
**Versión:** 2.0 Enterprise Cloud Multi-Tenant Adaptado a Venezuela  

---

## 🔒 1. Control de Acceso, Usuarios y Seguridad
1. **Acceso al Portal:** Ingrese su Nombre de Usuario o Correo y su Contraseña en la pantalla de inicio de sesión.
2. **Políticas Antihackeo:** Dispone de un máximo de 3 intentos consecutivos. Al tercer intento fallido, la cuenta se bloqueará por seguridad. El Administrador puede desbloquearla desde el panel de Usuarios.
3. **Soporte de Emergencia:** Si el Administrador bloquea su cuenta, contacte a **InfaGraSolution (Luis Infante al 0412-0161906 o infagrasolution@gmail.com)**.

---

## 📦 2. Módulo de Inventario y Almacenes (WMS)
* **Catálogo de Productos:** SKU único, código de barras EAN/UPC para lectores ópticos, fotografía del producto, categoría y cálculo de margen de ganancia.
* **Control de Stock Mínimo (Alarma de Stop):** El sistema alerta dinámicamente en el Dashboard cuando el inventario llega a niveles de reposición para evitar quiebres.
* **Productos a Granel:** Soporte para unidades de medida en kilogramos (`kg`), gramos (`gr`), metros (`mt`), litros (`lt`) con precisión de hasta 4 decimales (`1.450 kg`).
* **Multi-Almacén:** Gestión del Depósito Principal y Depósitos Externos (1, 2, etc.) con inventarios independientes.
* **Ubicaciones (Bin Locations):** Organización por Pasillo, Estante y Casillero con generación e impresión de etiquetas QR.
* **Movimientos Físicos:** Cargos (entradas manuales), Descargos (mermas/salidas) y Ajustes.
* **Transferencias y Notas de Despacho:** Traslados entre almacenes con emisión de Notas de Despacho en PDF.
* **Auditorías Físicas:** Conteo ciego vs. teórico y reporte de discrepancias.
* **Costo Promedio Ponderado:** Recálculo automático con cada recepción de compra.
* **Carga Masiva CSV:** Importación de catálogo y existencias iniciales mediante plantilla Excel en formato CSV.

---

## 🛒 3. Módulo de Ventas, Facturación y POS
* **Directorio de Clientes:** RIF/Cédula, dirección, teléfonos, límite de crédito en USD y días de crédito.
* **Punto de Venta (POS) Táctil:** Facturación rápida con teclado táctil y escaneo de códigos de barra USB/Bluetooth.
* **Gestión de Caja:** Aperturas con saldo inicial (Bs. y USD), cobros multimoneda combinados (Efectivo Bs/USD, Pago Móvil, Punto de Venta, Zelle, Crédito), cálculo automático de vueltos y arqueo de cierre con reporte de diferencias.
* **Impresoras Térmicas y Fiscales:** Compatible con impresoras térmicas de 58mm y 80mm, e impresoras fiscales homologadas por el SENIAT (**The Factory HKA, Bematech, Aclas**) vía agente local en puerto 8080.
* **Facturación en Forma Libre:** Facturación manual de contingencia.
* **Notas de Entrega a Clientes:** Emisión y descarga en PDF con formato corporativo, logotipo y firmas de recepción.
* **Presupuestos y Cotizaciones:** Cotizaciones con validez temporal y conversión inmediata a venta.
* **Notas de Crédito y Débito:** Procesamiento de devoluciones con reintegro automático de mercancía a stock.

---

## 🛍️ 4. Módulo de Compras y Proveedores
* **Proveedores:** RIF, persona de contacto, agente de retención y cuentas bancarias.
* **Órdenes de Compra y Recepción:** Recepción física en almacén con incremento de stock, recálculo de costo y generación de cuenta por pagar.
* **Retenciones:** Retenciones de IVA (75%) e ISLR con emisión de comprobantes.

---

## 🏦 5. Tesorería (Cuentas por Cobrar y por Pagar)
* **Cuentas por Cobrar (CxC):** Registro de ventas a crédito, historial de cobros, amortizaciones parciales en USD o Bs. y reporte de antigüedad de saldos.
* **Cuentas por Pagar (CxP):** Compromisos con proveedores y programación de pagos.
* **Cuentas Bancarias:** Conciliación bancaria en bolívares y divisas.

---

## 📑 6. Módulo Fiscal y Reportes SENIAT
* **Libros Oficiales:** Emisión automática de Libros de Compras y Ventas según la Providencia 0049.
* **IGTF (3%):** Cálculo y desglose del impuesto en pagos percibidos en moneda extranjera.

---

## 👥 7. Nómina y Gestión Humana (LOTTT)
* Expedientes de trabajadores, nóminas quincenales/mensuales, retenciones de ley (IVSS, FAOV, INCES), horas extras y recibos en PDF.

---

## 🚀 8. Soporte Técnico Oficial InfaGraSolution
* **Empresa:** InfaGraSolution  
* **Contacto Técnico:** Luis Infante  
* **Teléfono / WhatsApp:** 0412-0161906  
* **Correo Electrónico:** infagrasolution@gmail.com  
"""

SUPPORT_PHONE = "+584120161906"


@router.get("/")
async def view_manual(current_user: User = Depends(get_current_user)):
    """Retorna el manual de usuario en formato estructurado de texto para el frontend."""
    return {
        "title": "Manual de Usuario ERP - APEX",
        "language": "es",
        "content_markdown": MANUAL_TEXT_ES,
        "support_phone": SUPPORT_PHONE,
    }


@router.get("/download")
async def download_manual_file(current_user: User = Depends(get_current_user)):
    """Descarga el manual oficial de usuario en formato Markdown (.md) para fácil lectura o impresión."""
    file_like = io.BytesIO(MANUAL_TEXT_ES.encode("utf-8"))
    
    headers = {
        "Content-Disposition": "attachment; filename=manual_usuario_apex_erp.md"
    }
    return StreamingResponse(file_like, media_type="text/markdown", headers=headers)
