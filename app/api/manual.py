from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from app.api.deps import get_current_user
from app.domain.user import User
import io

router = APIRouter()

MANUAL_TEXT_ES = """# 📘 MANUAL DE USUARIO OFICIAL — APEX ERP VENEZUELA

Bienvenido al manual oficial de operaciones de **APEX ERP**, el sistema de gestión integrada y adaptada a la normativa legal, fiscal y comercial de Venezuela. Este documento le guiará a través del uso y mejores prácticas de cada módulo del sistema.

---

## 🔒 1. Control de Acceso y Seguridad de Sesión

### A. Acceso Seguro al Portal
1. Ingrese su **Nombre de Usuario** y su **Contraseña** en la pantalla principal.
2. Presione **Login** en el botón de color azul zafiro.
3. Al ingresar, se iniciará automáticamente el **Asistente Guiado (Wizard)** que le enseñará el funcionamiento básico paso a paso.

### B. Políticas de Bloqueo de Cuentas (Protección Antihackeo)
* **Intentos Fallidos Permitidos:** 3 intentos.
* **Bloqueo Operativo:** Al tercer intento fallido, la cuenta se bloquea por seguridad. Solicite al Administrador de su empresa que desbloquee la cuenta desde el panel de **Usuarios**.
* **Bloqueo del Administrador:** Si la cuenta del Administrador se bloquea, aparecerá una alerta de color rojo con un enlace directo a Soporte Técnico vía WhatsApp o al número **0412-0161906** para restablecer la contraseña de forma segura.

---

## 📦 2. Módulo de Inventario y Almacenes (WMS)

El módulo de Inventario centraliza el control físico y el valor monetario de toda la mercancía en tiempo real.

### A. Registro de Productos en el Catálogo
1. Diríjase a **Inventario > Catálogo**.
2. Presione el botón **Nuevo Producto**.
3. Ingrese los datos del SKU (Código único), descripción, precio base de venta y límites de stock (mínimos/máximos).
4. El sistema calculará el Costo Promedio Ponderado con cada nueva entrada comercial.

### B. Cargos y Descargos Físicos
* **Cargos (Ingresos manuales):** Permite ingresar existencias físicas al inventario (ejemplo: saldos iniciales, cuadres de auditoría).
* **Descargos (Salidas manuales):** Registra el retiro inmediato de mercancía justificando mermas, pérdidas o donaciones, descontando stock al instante.

---

## 🛒 3. Módulo de Ventas y Facturación (POS)

El Punto de Venta (POS) permite procesar facturas y cobros de manera ágil y dinámica en Bolívares y Divisas.

### A. Gestión de Caja
1. **Apertura de Caja:** Antes de vender, acceda a **Caja > Abrir Caja** e ingrese el saldo inicial físico disponible en Bs. y USD para cambio.
2. **Cierre de Caja:** Al terminar el turno, acceda a **Caja > Cierre de Caja** e ingrese el conteo físico recaudado para compararlo contra los totales de venta.

### B. Proceso de Venta
1. Vaya a **Ventas > Nueva Venta** (o el botón de POS).
2. Seleccione el cliente (o use Consumidor Final).
3. Busque y agregue los productos indicando cantidades.
4. Presione **Procesar Pago** y elija los métodos de pago (Efectivo, Pago Móvil, Punto de Venta o Divisas) y la moneda.

---

## 🛒 4. Módulo de Compras e Importaciones

Permite reponer stock y mantener actualizados los costos promedios ponderados del catálogo.

1. Vaya a **Compras > Registrar Compra**.
2. Ingrese el Proveedor y agregue los ítems detallando cantidad y **costo unitario de compra actual**.
3. Al guardar, el inventario se incrementa síncronamente y el costo de catálogo se recalcula automáticamente.

---

## 🏦 5. Cuentas por Cobrar (CxC) y Cuentas por Pagar (CxP)

* **Cuentas por Cobrar (CxC):** Registra saldos pendientes de clientes generados por ventas a crédito. Permite registrar abonos parciales ordenadamente.
* **Cuentas por Pagar (CxP):** Registra compromisos adquiridos con proveedores por compras a plazos, facilitando la planeación de egresos.

---

## 📝 6. Bitácora Universal de Movimientos

Todas las operaciones críticas se graban de manera automática e inmutable en el Historial Universal de Movimientos, detallando fecha, hora, usuario y descripción exacta, garantizando auditorías 100% transparentes.

---

## 📥 7. Importación Masiva de Datos (Carga Inicial)

Para facilitar la migración de datos desde otros sistemas o desde Excel, APEX ERP cuenta con herramientas de carga masiva mediante archivos **CSV** (Valores separados por comas).

### A. Carga Inicial de Inventario y Productos
1. Vaya a **Inventario > Catálogo**.
2. Presione **Importar Cargo Inicial**.
3. Haga clic en **Descargar Plantilla** para obtener el archivo de ejemplo.
4. Llene la plantilla en Excel (sin modificar los encabezados) y guárdela asegurándose de elegir el formato **CSV**.
5. Suba el archivo. El sistema creará los productos que no existan y registrará un **Cargo de Inventario** por las cantidades indicadas.

### B. Directorio de Clientes y Proveedores
1. Diríjase al módulo de **Clientes** (en Ventas) o **Proveedores** (en Compras/Inventario).
2. Presione el botón **Plantilla CSV** para descargar la estructura requerida.
3. Llene los datos requeridos (Nombre, RIF, Teléfono, etc.) y guarde el archivo como CSV.
4. Haga clic en **Importar** y seleccione su archivo. El sistema registrará todo el directorio en un instante.
> **Importante:** Si un RIF/Identificación fiscal ya existe en la base de datos, el sistema actualizará los datos de contacto en lugar de crear un duplicado.
"""


@router.get("/")
async def view_manual(current_user: User = Depends(get_current_user)):
    """Retorna el manual de usuario en formato estructurado de texto para el frontend."""
    return {
        "title": "Manual de Usuario ERP - APEX",
        "language": "es",
        "content_markdown": MANUAL_TEXT_ES,
        "support_phone": SUPPORT_PHONE,
    }


SUPPORT_PHONE = "+584120161906"


@router.get("/download")
async def download_manual_file(current_user: User = Depends(get_current_user)):
    """Descarga el manual oficial de usuario en formato Markdown (.md) para fácil lectura o impresión."""
    file_like = io.BytesIO(MANUAL_TEXT_ES.encode("utf-8"))
    
    headers = {
        "Content-Disposition": "attachment; filename=manual_usuario_apex_erp.md"
    }
    return StreamingResponse(file_like, media_type="text/markdown", headers=headers)
