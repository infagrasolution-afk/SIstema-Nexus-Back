from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_user
from app.domain.user import User
import io

router = APIRouter()

MANUAL_TEXT_ES = """# 📘 MANUAL DE USUARIO OFICIAL — APEX ERP

> **Desarrollado con orgullo en Venezuela por:** InfaGraSolution  
> **Director de Sistemas / Soporte:** Luis Infante  
> **Teléfono / WhatsApp:** +58 412-0161906  
> **Correo Electrónico:** infagrasolution@gmail.com  
> **Versión del Sistema:** 2.1 Enterprise Cloud (Edición Especial para Empresas en Venezuela)

---

## 👋 ¡Bienvenido a APEX ERP!

**APEX ERP** es un sistema administrativo integral diseñado especialmente para el comercio, distribuidoras y empresas de servicios en Venezuela. Su objetivo es facilitarle el trabajo diario: desde emitir una factura rápida en caja hasta llevar el control exacto de su inventario, sus ganancias reales, sus cuentas por cobrar en dólares y bolívares, y cumplir con todas las normativas legales vigentes del **SENIAT** y de la **LOTTT**.

Este manual está redactado en lenguaje sencillo y práctico para que cualquier persona del equipo (cajeros, vendedores, almacenistas, contadores y dueños de negocio) aprenda a usar el sistema en pocos minutos.

---

## 🔒 1. Inicio de Sesión y Seguridad de tu Cuenta

Para proteger los datos de tu empresa contra accesos no autorizados, el sistema cuenta con medidas de seguridad de nivel bancario:

1. **Acceso al Sistema:**
   - Ingresa tu **Nombre de Usuario** y tu **Contraseña** secreta.
   - Presiona el botón **Iniciar Sesión**.
2. **Protección contra Intentos Fallidos (Bloqueo Preventivo):**
   - Dispones de hasta **3 intentos consecutivos** para ingresar tu clave correcta.
   - Si introduces la clave incorrecta 3 veces seguidas, el sistema **bloqueará temporalmente la cuenta** para evitar ataques automáticos de piratas informáticos.
   - **¿Qué hacer si te bloqueas?**
     - Si eres un usuario o empleado: tu Administrador de Empresa puede ingresar al módulo de **Usuarios** y hacer clic en el botón de candado **Desbloquear Cuenta**.
     - También puedes esperar 15 minutos para que el sistema se desbloquee automáticamente.
     - Si eres el Administrador y no recuerdas la clave: contacta de inmediato al soporte técnico oficial de InfaGraSolution por WhatsApp al **0412-0161906**.
3. **Control de Sesión Única:**
   - Por seguridad de tu caja y de tu información, si inicias sesión en otra computadora o navegador, la sesión anterior en la otra máquina se cerrará automáticamente, evitando que dos personas usen la misma cuenta al mismo tiempo.
4. **Cierre de Sesión:**
   - Al terminar tu turno o abandonar tu puesto de trabajo, haz clic en tu nombre en la esquina superior derecha y selecciona **Cerrar Sesión**.

---

## 👥 2. Gestión de Usuarios y Permisos de Empleados

Como dueño o administrador de la empresa, tú decides qué puede ver y hacer cada trabajador:

1. **Nivel Administrador de Empresa:**
   - Tiene acceso completo a todos los módulos contratados, reportes de ganancias, configuración de la empresa y creación de nuevos usuarios.
2. **Usuarios Operativos con Roles Específicos:**
   - **Cajero:** Solo tiene acceso al Punto de Venta (POS) y a la apertura/cierre de su propia caja. No puede ver las ganancias ni modificar la configuración.
   - **Vendedor:** Puede emitir presupuestos, consultar precios e inventario disponible, y registrar clientes.
   - **Almacenista:** Puede recibir mercancía de proveedores, realizar transferencias entre depósitos y registrar entradas o salidas físicas, pero no ve finanzas ni dinero.
   - **Contador:** Acceso a cuentas contables, conciliación bancaria, reportes de ingresos/egresos y libros fiscales del SENIAT.
   - **Especialista de RRHH:** Maneja la ficha de trabajadores, cálculo de nómina y recibos de pago.
3. **¿Cómo crear un nuevo usuario?**
   - Ve a **Usuarios** en el menú principal.
   - Haz clic en **Crear Nuevo Usuario**.
   - Ingresa el nombre de usuario, correo, una **contraseña segura de mínimo 8 caracteres** y selecciona su nivel de acceso o rol.
   - Presiona **Guardar**.

---

## 📦 3. Inventario y Control de Almacenes

Mantén tus existencias al día y evita pérdidas o quiebres de mercancía:

1. **Registrar un Producto:**
   - Dirígete a **Inventario** → **Productos** y presiona **Nuevo Producto**.
   - Ingresa el **Nombre del Producto**, código de barra (puedes escanearlo directamente con la pistola lectora), categoría y unidad de medida (unidades, kilos, litros, metros).
   - Establece el **Costo de Compra** y el **Precio de Venta** en dólares (USD). El sistema calculará automáticamente el equivalente en bolívares según la tasa oficial del BCV.
   - Define el **Stock Mínimo (Alarma de Parada)**: cuando las existencias lleguen a este número, el sistema te avisará con una alerta amarilla en el tablero principal para que vuelvas a comprar a tiempo.
2. **Productos a Granel (Pesados o Fraccionados):**
   - El sistema admite hasta 4 decimales. Si vendes queso, carne, tornillos o pintura, puedes vender `1.450 kg` o `0.250 lt` con total exactitud.
3. **Múltiples Almacenes y Depósitos:**
   - Si cuentas con un Depósito Principal y sucursales o depósitos externos, puedes transferir mercancía entre ellos usando **Inventario** → **Transferencias**, emitiendo una **Nota de Despacho** para el chofer o encargado del traslado.
4. **Cargos y Descargos de Mercancía:**
   - **Cargo (Entrada):** Para ingresar mercancía que no provenga de compra directa (sobrantes, fabricación propia).
   - **Descargo (Salida):** Para retirar mercancía por merma, rotura, vencimiento o uso interno del negocio.
5. **Auditorías Físicas (Conteo a ciegas):**
   - Permite a tus empleados contar físicamente los estantes sin ver la cantidad teórica del sistema. Luego el sistema compara ambos números y te genera un reporte de sobrantes y faltantes.

---

## 🛒 4. Ventas y Punto de Venta (POS) Táctil

Diseñado para cobrar a máxima velocidad en mostradores y cajas:

1. **Abrir la Caja al Iniciar el Día:**
   - Ve a **Caja** → **Abrir Caja**.
   - Registra tu base o saldo inicial de efectivo (en Bolívares y en Dólares en efectivo).
2. **Cobrar una Venta:**
   - En el **Punto de Venta (POS)**, busca el producto por nombre o pásalo por el lector de código de barras.
   - Puedes seleccionar un cliente existente o registrar uno nuevo al instante indicando su Cédula o RIF.
   - Presiona **Cobrar (F12)**.
3. **Pagos Multimoneda Combinados (Bimonetario):**
   - Un cliente en Venezuela puede pagarte, por ejemplo, una parte en Dólares en efectivo, otra en Pago Móvil y el resto con tarjeta en el Punto de Venta bancario.
   - Selecciona los métodos de pago utilizados y el sistema calculará automáticamente el vuelto exacto en Bolívares o Dólares.
4. **Impresión de Documentos:**
   - Compatible con impresoras térmicas de tickets (58mm y 80mm).
   - Compatible con impresoras fiscales homologadas por el SENIAT (**The Factory HKA, Bematech, Aclas, Bixolon, Custom**) a través del conector fiscal local.
   - Generación de **Notas de Entrega** y facturas en formato PDF con el logo y membrete de tu empresa.
5. **Cierre de Caja y Arqueo al Final del Turno:**
   - Haz clic en **Cerrar Caja**.
   - Cuenta el dinero físico que tienes en la gaveta y escríbelo en la pantalla.
   - El sistema comparará lo cobrado según el sistema con lo que tienes en mano e imprimirá el reporte de cierre con la diferencia (cuadrado, sobrante o faltante).

---

## 🛍️ 5. Compras y Cuentas con Proveedores

1. **Registrar Facturas de Proveedores:**
   - En **Compras** → **Nueva Compra**, selecciona el proveedor e ingresa el número de factura y número de control.
   - Al cargar los productos, el sistema **aumenta automáticamente las existencias** en el almacén seleccionado y actualiza el **Costo Promedio Ponderado**.
2. **Retenciones de IVA e ISLR:**
   - Si tu empresa es Agente de Retención designado por el SENIAT, el sistema calcula automáticamente el 75% o 100% de retención de IVA y emite el comprobante en PDF listo para imprimir o enviar por correo.

---

## 🏦 6. Tesorería (Cuentas por Cobrar y por Pagar)

1. **Cuentas por Cobrar (Clientes que te deben):**
   - Cuando realizas una venta a crédito, se genera una cuenta por cobrar asociada al cliente.
   - Puedes registrar abonos parciales o pagos totales en cualquier moneda (Bs. o USD) a la tasa del día, manteniendo el historial de pagos y saldo pendiente.
2. **Cuentas por Pagar (Proveedores a los que les debes):**
   - Lleva el control de tus fechas de vencimiento para no retrasarte en los compromisos comerciales con tus suplidores.

---

## 📑 7. Cumplimiento Fiscal SENIAT (Venezuela)

1. **Libro Oficial de Ventas y Libro de Compras:**
   - Generados automáticamente según lo establecido en la **Providencia Administrativa N° 0049 del SENIAT**.
   - Incluye desglose de base imponible, exentos, alícuota general (16%), alícuotas reducidas y retenciones practicadas.
   - Puedes descargarlos en formato Excel (CSV) para tu contador.
2. **IGTF (Impuesto a las Grandes Transacciones Financieras 3%):**
   - El sistema calcula y desglosa de forma automática el 3% cuando el cliente paga en divisas o moneda extranjera en efectivo.

---

## 👥 8. Nómina y Gestión Humana (LOTTT)

1. **Expedientes de Trabajadores:**
   - Registra nombres, cédula, cargo, fecha de ingreso, salario base en USD o Bs., y modalidad de pago (quincenal o mensual).
2. **Cálculo Automático de Deducciones de Ley:**
   - Seguro Social Obligatorio (**IVSS** - 4%).
   - Régimen Prestacional de Empleo (**Paro Forzoso** - 0.5%).
   - Fondo de Ahorro Obligatorio para la Vivienda (**FAOV** - 1%).
   - **Cestaticket Socialista** indexado.
3. **Recibos de Pago en PDF:**
   - Emite e imprime los recibos individuales con duplicado para la firma del trabajador.

---

## 💾 9. Respaldo y Seguridad de los Datos

Tu tranquilidad es nuestra prioridad:

1. **Copia de Seguridad Automática:**
   - La base de datos central en la nube cuenta con réplica continua y cifrado de extremo a extremo.
2. **Descarga de Copia Local (Script de Respaldo):**
   - El administrador técnico puede ejecutar el comando de respaldo para descargar un archivo comprimido `.json.gz` con toda la información de la empresa.
3. **Prevención contra Pérdidas:**
   - Las ventas y documentos fiscales no se borran; quedan anulados con motivo justificado para preservar la integridad contable y la trazabilidad requerida por la ley venezolana.

---

## 📞 10. Canales de Asistencia y Soporte Oficial

Si tienes dudas, requieres capacitación para tu personal o necesitas activar nuevos módulos:

* **Empresa Proveedora:** InfaGraSolution  
* **Responsable Técnico:** Luis Infante  
* **WhatsApp / Llamadas Directas:** 0412-0161906 (+58 412 016 1906)  
* **Correo de Atención al Cliente:** infagrasolution@gmail.com  
* **Horario de Soporte:** Lunes a Sábado de 8:00 AM a 7:00 PM (Guardia de emergencias en fin de semana para comercios activos).
"""

SUPPORT_PHONE = "+584120161906"


@router.get("/")
async def view_manual(current_user: User = Depends(get_current_user)):
    """Retorna el manual de usuario en formato estructurado para el lector integrado del sistema."""
    return {
        "title": "Manual de Operaciones Oficial — APEX ERP",
        "language": "es-VE",
        "content_markdown": MANUAL_TEXT_ES,
        "support_phone": SUPPORT_PHONE,
    }


@router.get("/download")
async def download_manual_file(current_user: User = Depends(get_current_user)):
    """Descarga el manual oficial de usuario en formato Markdown (.md) para fácil lectura o impresión."""
    file_like = io.BytesIO(MANUAL_TEXT_ES.encode("utf-8"))
    
    headers = {
        "Content-Disposition": "attachment; filename=manual_usuario_apex_erp_venezuela.md"
    }
    return StreamingResponse(file_like, media_type="text/markdown", headers=headers)
