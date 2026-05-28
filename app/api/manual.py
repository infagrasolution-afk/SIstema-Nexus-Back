from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from app.api.deps import get_current_user
from app.domain.user import User
import io

router = APIRouter()

MANUAL_TEXT_ES = """# 📘 MANUAL DE USUARIO ERP — NEXUS VENEZUELA

Bienvenido al manual oficial de usuario de **NEXUS ERP**, el sistema de gestión integral adaptado a la normativa y realidad comercial de Venezuela. Este documento le guiará a través del uso correcto de cada módulo operativo y administrativo.

---

## 🔒 1. Acceso y Control de Seguridad

### Ingreso al Sistema
1. Introduzca su **Nombre de Usuario** y **Contraseña**.
2. Presione **Iniciar Sesión**.

### Bloqueo de Cuentas (Políticas de Seguridad)
* **Intentos Permitidos:** 3 intentos fallidos.
* **Usuarios Operativos:** Si se equivoca 3 veces, su cuenta se bloqueará por seguridad. Solicite al **Administrador de su Empresa** el desbloqueo desde la pantalla de *Gestión de Usuarios*.
* **Administrador del Sistema:** Si la cuenta del Administrador se bloquea, la pantalla mostrará una alerta de color rojo con un enlace directo para contactar a Soporte Técnico vía WhatsApp o vía telefónica al **0412-0161906** para verificar su identidad, realizar el desbloqueo y restablecer su clave de acceso de manera segura.

---

## 📦 2. Módulo de Inventario (WMS)

El módulo de Inventario gestiona la existencia de mercancías en tiempo real.

### Registrar Productos
1. Vaya a **Inventario > Productos** y haga clic en **Nuevo Producto**.
2. Introduzca el **SKU (Código Único)**, el nombre, la categoría, el stock mínimo y máximo, y la unidad de medida (Ej: unidad, kg, caja).
3. **Costo Promedio:** El sistema calcula de manera automática el costo promedio ponderado de sus productos con cada compra o ingreso con costo unitario.

### Operaciones de Inventario
* **Cargo de Inventario (Ingreso manual):** Utilizado para saldos iniciales o ingresos extraordinarios. Afecta el stock sumándolo.
* **Descargo de Inventario (Salida manual):** Utilizado para mercancías dañadas, perdidas, donaciones o retiros del almacén. Resta stock de manera inmediata.
* **Ajustes:** Cambios manuales para cuadrar inventarios físicos.
* **Transferencias:** Mueve mercancía entre diferentes almacenes (Ej: de Depósito Principal a Almacén Sucursal) sin afectar el inventario total general.

---

## 🛒 3. Módulo de Ventas y Facturación

### Registrar Ventas
1. Ingrese a **Ventas > Nueva Venta**.
2. Seleccione el cliente (o ingrese un cliente genérico "Consumidor Final").
3. Busque el producto por SKU o nombre, ingrese la cantidad y agréguelo a la lista.
4. Elija el **Método de Pago** (Efectivo, Transferencia, Pago Móvil, Punto de Venta o Divisas) y la moneda.
5. Presione **Procesar Venta**.
   * *Afectación de Stock:* Al procesar, el sistema descuenta de forma automática el stock correspondiente del almacén seleccionado.
   * *Trazabilidad:* Se registra la venta en la bitácora universal de movimientos.

### Presupuestos y Notas de Entrega
* **Presupuestos:** Permite crear una cotización sin comprometer stock. Puede ser convertida a Venta posteriormente.
* **Notas de Entrega:** Documentos que justifican el despacho físico de mercancía al cliente.

---

## 📈 4. Módulo de Compras e Importaciones

### Registrar Compras
1. Vaya a **Compras > Registrar Compra**.
2. Seleccione el Proveedor (o cree uno nuevo con su RIF/Cédula).
3. Agregue los productos comprados indicando la cantidad e **importante:** el costo unitario de compra actual.
4. Presione **Guardar Compra**.
   * *Stock:* Suma existencias automáticamente al almacén seleccionado.
   * *Costo Promedio:* Recalcula el costo promedio del producto en base al nuevo precio de compra.
   * *Trazabilidad:* Genera un registro en la bitácora universal de movimientos.

---

## 🏦 5. Módulo de Tesorería (CxC / CxP)

Monitorea las deudas pendientes con clientes y proveedores.

* **Cuentas por Cobrar (CxC):** Generadas automáticamente en ventas a crédito. Permite registrar abonos parciales o totales hasta liquidar la factura.
* **Cuentas por Pagar (CxP):** Generadas automáticamente en compras a crédito con proveedores. Registre los egresos de dinero ordenadamente.

---

## 📝 6. Bitácora Universal de Movimientos

El ERP cuenta con una **Tabla Maestra de Movimientos (`SystemMovement`)** inmutable. Cada vez que realice un Cargo, Descargo, Ajuste, Venta, Compra, Despacho, Pago de CxC/CxP o Apertura/Cierre de Caja, el sistema graba de forma automática:
1. La fecha y hora exacta.
2. El usuario que lo realizó.
3. El módulo y la operación.
4. Detalles del producto, almacén y cantidad (si aplica).
5. Montos monetarios involucrados.
6. Descripción automática estructurada para auditorías transparentes.

*Para consultar este historial, vaya a **Reportes > Historial Universal de Movimientos**.*

---

## 🔧 7. Administración de la Empresa (Para el Administrador)

### Crear y Gestionar Usuarios
Como Administrador de la Empresa, usted puede crear cuentas adicionales para sus empleados:
1. Ingrese a **Administración > Usuarios** y presione **Nuevo Usuario**.
2. Asigne un **Rol** de trabajo para que el usuario solo pueda ver y realizar operaciones autorizadas:
   * **Vendedor:** Limitado a ventas, consultar inventario y caja.
   * **Almacenista:** Limitado a cargos, descargos, transferencias y despachos.
   * **Contador:** Acceso a reportes, contabilidad y tesorería.
   * **Cajero:** Operaciones de caja diarias.
3. Defina los **Módulos Activos** que puede visualizar ese usuario en su menú lateral.
"""


@router.get("/")
async def view_manual(current_user: User = Depends(get_current_user)):
    """Retorna el manual de usuario en formato estructurado de texto para el frontend."""
    return {
        "title": "Manual de Usuario ERP - NEXUS",
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
        "Content-Disposition": "attachment; filename=manual_usuario_nexus_erp.md"
    }
    return StreamingResponse(file_like, media_type="text/markdown", headers=headers)
