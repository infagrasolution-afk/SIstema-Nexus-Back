# 📗 Manual Funcional de Usuario — Sistema Nexus ERP
> **Versión 2.0 Enterprise** · Infagra Solution · Sistema de Gestión Empresarial Multi-Tenant  
> *Diseñado para empresas comerciales, industriales y de servicios con soporte multi-moneda (USD / Bs. BCV).*

---

## 📑 Tabla de Contenidos

1. [Visión General del Sistema](#1-visión-general-del-sistema)
2. [Acceso, Autenticación y Navegación](#2-acceso-autenticación-y-navegación)
3. [Panel de Control (Dashboard)](#3-panel-de-control-dashboard)
4. [Módulo de Ventas y Facturación](#4-módulo-de-ventas-y-facturación)
5. [Módulo de Punto de Venta (POS) y Gestión de Caja](#5-módulo-de-punto-de-venta-pos-y-gestión-de-caja)
6. [Módulo de Inventario y Almacenes (WMS)](#6-módulo-de-inventario-y-almacenes-wms)
7. [Módulo de Compras y Proveedores](#7-módulo-de-compras-y-proveedores)
8. [Módulo de Tesorería (CxC, CxP y Conciliación Bancaria)](#8-módulo-de-tesorería-cxc-cxp-y-conciliación-bancaria)
9. [Módulo Fiscal y Retenciones SENIAT (Providencia 0049)](#9-módulo-fiscal-y-reportes-seniat)
10. [Módulo de Nómina y Recursos Humanos (LOTTT Venezuela)](#10-módulo-de-nómina-y-recursos-humanos-lottt-venezuela)
11. [Módulo de Contabilidad General VEN-NIF](#11-módulo-de-contabilidad-general-ven-nif)
12. [Módulo de Configuración, Roles y Auditoría](#12-módulo-de-configuración-roles-y-auditoría)
13. [Preguntas Frecuentes (FAQ) y Soporte](#13-preguntas-frecuentes-faq-y-soporte)

---

## 1. Visión General del Sistema

**Nexus ERP** es una plataforma integral de planificación de recursos empresariales en la nube. Está estructurada bajo un esquema multi-inquilino (*multi-tenant*), lo que garantiza el aislamiento absoluto de los datos de su empresa respecto a otras organizaciones.

### Características Principales:
* **Moneda Dual Nativa:** Operación simultánea en Dólares Americanos ($ USD) y Bolívares (Bs.), con actualización automática o manual de la tasa oficial del Banco Central de Venezuela (BCV).
* **Integración en Tiempo Real:** Las ventas descuentan inventario inmediatamente, generan cuentas por cobrar (si aplica), alimentan el libro fiscal y registran asientos contables automáticos.
* **Seguridad Basada en Roles (RBAC):** Cada usuario tiene acceso estrictamente limitado a las funciones y pantallas requeridas para su puesto de trabajo.
* **Trazabilidad Completa:** Toda acción crítica (creación, edición, anulación o eliminación) queda registrada en una bitácora inmutable de auditoría.

---

## 2. Acceso, Autenticación y Navegación

### 2.1. Inicio de Sesión
1. Abra su navegador web (Google Chrome, Mozilla Firefox o Microsoft Edge recomendados) e ingrese a la dirección del ERP.
2. Ingrese su **Nombre de Usuario** o **Correo Electrónico** registrado.
3. Ingrese su **Contraseña**.
4. Haga clic en el botón **"Iniciar Sesión"**.
5. Si sus credenciales son válidas, el sistema cargará su panel de trabajo según los permisos asignados a su rol.

> 🔒 **Seguridad y Cierre por Inactividad:** Por política de seguridad bancaria y corporativa, si permanece inactivo por más de 15 minutos sin interactuar con el sistema, su sesión se cerrará de forma automática para proteger la información de la empresa.

### 2.2. Recuperación o Cambio de Contraseña
* Para cambiar su contraseña personal:
  1. Haga clic en su avatar o nombre de usuario en la esquina superior derecha.
  2. Seleccione **"Mi Perfil"**.
  3. En la sección **Seguridad**, escriba su contraseña actual y luego la nueva contraseña (mínimo 8 caracteres, incluyendo letras y números).
  4. Presione **"Guardar Cambios"**.

### 2.3. Barra de Navegación Lateral (Sidebar)
El menú lateral agrupa las funciones principales del sistema:
* 📊 **Dashboard:** Métricas ejecutivas y KPIs operacionales.
* 🛒 **Ventas:** Facturación, cotizaciones, notas de crédito/débito y clientes.
* 💳 **Caja / POS:** Terminal de cobro rápido, aperturas, arqueos y cierres de turno.
* 📦 **Inventario:** Productos, almacenes, lotes, movimientos y despachos.
* 🛍️ **Compras:** Proveedores, órdenes de compra y recepción de insumos.
* 💰 **Tesorería:** Cuentas por cobrar (CxC), cuentas por pagar (CxP) y bancos.
* 📑 **Fiscal:** Libros de ventas y compras oficiales formato SENIAT.
* ⚖️ **Contabilidad:** Plan de cuentas, asientos y balance de comprobación.
* ⚙️ **Configuración:** Parámetros de empresa, sucursales, roles y bitácora.

---

## 3. Panel de Control (Dashboard)

El Dashboard es el centro neurálgico del ERP. Permite a los directores, gerentes y administradores evaluar la salud operativa y financiera del negocio en segundos.

### 3.1. Indicadores Clave de Rendimiento (KPIs)
* **Ventas del Mes:** Monto acumulado facturado en USD y Bs. al tipo de cambio BCV.
* **Cobranzas Realizadas:** Total cobrado durante el ciclo actual.
* **Cuentas por Cobrar Pendientes:** Cartera vencida y por vencer de clientes.
* **Cuentas por Pagar a Proveedores:** Compromisos inmediatos de tesorería.
* **Valor del Inventario:** Costo total de las existencias disponibles en almacén.
* **Alertas de Stock Crítico:** Cantidad de productos cuya existencia está por debajo del umbral mínimo de seguridad.

### 3.2. Gráficas y Reportes Dinámicos
* **Tendencia de Ventas (Semanal / Mensual):** Gráfica de líneas que compara las ventas brutas frente al costo de ventas.
* **Top 10 Productos Más Vendidos:** Ranking por unidades vendidas y rentabilidad neta.
* **Flujo de Caja Proyectado:** Comparación visual entre ingresos esperados (CxC) y egresos comprometidos (CxP) para los próximos 30 días.

---

## 4. Módulo de Ventas y Facturación

El módulo de ventas gestiona todo el ciclo comercial, desde la propuesta preliminar hasta el cobro y la emisión del documento fiscal.

### 4.1. Catálogo de Clientes
* **Registrar un Nuevo Cliente:**
  1. Diríjase a **Ventas > Clientes** y presione **"+ Nuevo Cliente"**.
  2. Complete los campos obligatorios:
     * **Tipo de Documento y Número:** (V, E, J, G seguido del RIF o Cédula).
     * **Razón Social / Nombre Completo:** Nombre fiscal del cliente.
     * **Dirección Fiscal:** Calle, ciudad y estado.
     * **Teléfono y Correo Electrónico:** Para el envío de presupuestos y facturas en formato digital.
     * **Límite de Crédito y Días de Crédito:** En caso de que se le otorguen condiciones de crédito (ej. 15, 30 días).
  3. Presione **"Guardar Cliente"**.
* **Importación Masiva de Clientes:** Puede descargar la plantilla CSV estándar, completarla en Excel y cargar cientos de clientes en un solo clic.

### 4.2. Presupuestos y Cotizaciones
1. Ingrese a **Ventas > Cotizaciones** y haga clic en **"+ Nueva Cotización"**.
2. Seleccione el cliente y la fecha de vigencia (validez de la oferta).
3. Agregue los productos con sus cantidades y descuentos aplicables. El sistema mostrará los precios calculados en USD y el equivalente en Bolívares según la tasa BCV del día.
4. Guarde el presupuesto. Puede imprimirlo o enviarlo en PDF al cliente.
5. **Aprobación:** Cuando el cliente acepte la propuesta, abra la cotización y presione **"Aprobar y Facturar"**. Todos los ítems se trasladarán a la pantalla de ventas sin necesidad de volver a ingresarlos.

### 4.3. Facturación de Venta
1. Diríjase a **Ventas > Nueva Venta**.
2. Seleccione el cliente (o *Cliente de Contado General* para ventas rápidas).
3. Seleccione el **Almacén de Despacho** (por defecto: Almacén Principal).
4. Agregue los productos mediante el buscador inteligente (por código SKU, nombre o escaneando el código de barras).
5. Ingrese la forma de pago:
   * **Contado Inmediato:** Efectivo $, Efectivo Bs., Punto de Venta, Pago Móvil, Zelle o Transferencia. Puede combinar múltiples métodos de pago en una sola venta (pago mixto).
   * **Crédito:** Si el cliente tiene crédito habilitado, seleccione el plazo acordado. Se creará automáticamente un registro en **Cuentas por Cobrar (CxC)**.
6. Guarde la venta:
   * **Completar Venta:** Genera el correlativo fiscal, descuenta el stock de inmediato de los almacenes involucrados y emite la factura lista para imprimir.
   * **Guardar en Espera (On Hold):** Permite retener la venta en caso de que el cliente desee continuar agregando productos más tarde. *Nota: La venta en espera reserva el carrito pero no descuenta stock definitivo hasta ser completada.*

### 4.4. Notas de Crédito y Notas de Débito
* **Emisión de Nota de Crédito (Devolución o Descuento):**
  1. Vaya a **Ventas > Facturas** y localice la factura original.
  2. Presione la opción **"Emitir Nota de Crédito"**.
  3. Indique el motivo (Devolución total, devolución parcial o corrección de precio).
  4. Indique los productos y cantidades a reingresar al inventario.
  5. Al confirmar, el sistema:
     * Genera el comprobante fiscal correlativo de Nota de Crédito.
     * Reintegra los productos al stock del almacén seleccionado.
     * Ajusta el saldo pendiente en Cuentas por Cobrar o genera un saldo a favor del cliente.

### 4.5. Anulación de Facturas
Si una factura fue emitida con error el mismo día de la operación y antes del cierre contable/caja:
1. Acceda al detalle de la venta con permiso administrativo (`sales:void`).
2. Haga clic en **"Anular Factura"**.
3. Ingrese la justificación formal de la anulación.
4. El sistema reintegrará el inventario, anulará la cuenta por cobrar y marcará el documento fiscal como anulado para el Libro de Ventas SENIAT.

---

## 5. Módulo de Punto de Venta (POS) y Gestión de Caja

Diseñado para locales comerciales, sucursales y puntos de alta rotación donde se requiere cobrar con rapidez y controlar el flujo de dinero en efectivo y electrónico.

### 5.1. Apertura de Turno de Caja
1. Al iniciar la jornada laboral, el cajero debe ingresar a **Caja > Apertura de Turno**.
2. Indique el **Fondo Inicial de Caja** (dinero en efectivo destinado a dar cambio/vuelto), desglosado por moneda:
   * Efectivo USD ($).
   * Efectivo Bolívares (Bs.).
3. Presione **"Abrir Turno"**. A partir de este momento, todas las ventas de mostrador del usuario quedarán asociadas a su sesión activa.

### 5.2. Operación de Cobro Multimoneda
Durante el cobro en el POS:
* El cajero puede ingresar el monto recibido en diferentes denominaciones. Por ejemplo: una cuenta de 45 USD puede pagarse con un billete de $20 USD en efectivo y el resto en Bolívares vía Pago Móvil según la tasa BCV.
* El sistema calcula de inmediato el vuelto exacto a entregar en la moneda seleccionada, minimizando errores humanos.

### 5.3. Arqueo Intermedio y Retiros de Caja
* **Retiro de Efectivo:** Si la caja acumula un exceso de efectivo por seguridad, el supervisor puede registrar un **"Retiro de Caja"** hacia la bóveda central o depósito bancario.
* **Arqueo Ciego:** El supervisor puede solicitar al cajero el conteo físico del dinero en cualquier momento para compararlo contra los ingresos registrados en el sistema.

### 5.4. Reporte de Cierre de Caja (Corte X / Cierre Z)
1. Al finalizar el turno o la jornada comercial, diríjase a **Caja > Cierre de Turno**.
2. El cajero ingresa los montos físicos contados en gaveta (conteo a ciegas).
3. Presione **"Generar Reporte de Cierre"**.
4. El sistema emite el comprobante oficial con:
   * Total ventas brutas y netas.
   * Desglose exacto por método de pago: Efectivo USD, Efectivo Bs., Punto de Venta (lote bancario), Pago Móvil, Zelle, Transferencias.
   * Diferencias detectadas (Sobrante o Faltante de caja).
5. Confirme el cierre definitivo.

---

## 6. Módulo de Inventario y Almacenes (WMS)

El módulo de inventario controla el ciclo de vida de los productos, su almacenamiento físico, costos y niveles de reposición.

### 6.1. Gestión de Productos
* **Ficha Técnica del Producto:**
  * **SKU / Código Único:** Identificador alfanumérico principal.
  * **Código de Barras:** Para lectura con lector láser o pistola USB.
  * **Nombre y Descripción Detallada.**
  * **Categoría y Subcategoría:** Para reportería agrupada.
  * **Unidad de Medida:** Unidad (UND), Kilogramo (KG), Litro (LT), Metro (MT), Caja, etc.
  * **Costo Base ($ USD):** Costo de adquisición ante el proveedor.
  * **Margen de Ganancia (%):** Porcentaje comercial deseado.
  * **Precio de Venta ($ USD y Bs. BCV):** Calculado automáticamente según el margen o fijado manualmente.
  * **Aplica IVA:** Indique si el ítem está exento (0%), gravado a tasa general (16%) o tasa reducida (8%).
  * **Stock Mínimo y Máximo:** Parámetros para disparar alertas automáticas de reabastecimiento.

### 6.2. Múltiples Almacenes y Ubicaciones (WMS)
* Nexus ERP soporta múltiples depósitos físicos (ej. Almacén Central, Bodega Caracas, Almacén de Tránsito, Tienda Física 1).
* **Ubicaciones Bin/Rack:** Cada producto puede asociarse a un pasillo, estante o casillero específico (ej. `Pasillo A - Estante 3 - Nivel 2`) para agilizar el proceso de preparación de pedidos (*picking*).

### 6.3. Trazabilidad por Lotes (Batches)
* Para productos perecederos, farmacéuticos o de control serial:
  * Registro de **Número de Lote** al momento de la compra o recepción.
  * Registro de **Fecha de Vencimiento / Caducidad**.
  * Al despachar o facturar, el sistema prioriza la salida bajo la regla **FIFO/PEPS** (Primero en entrar, primero en salir) para evitar mermas por expiración.

### 6.4. Movimientos de Inventario
* **Cargos de Inventario (Entrada):** Ajuste positivo para ingresar stock no proveniente de compras ordinarias (ej. inventario inicial, donaciones recibidas, sobrantes justificados).
* **Descargos de Inventario (Salida):** Ajuste negativo para dar de baja mercancía dañada, vencida, muestras comerciales o mermas de almacén. Todo descargo exige una justificación obligatoria.
* **Transferencias entre Almacenes:** Traslado de mercancía entre sucursales.
* **Notas de Despacho:** Control del estado del traslado:
  1. `PENDING` (En preparación).
  2. `IN_TRANSIT` (En ruta con el transportista).
  3. `RECEIVED` (Recibido y verificado en el almacén de destino).

### 6.5. Auditorías de Inventario (Conteo Físico)
1. Vaya a **Inventario > Auditorías** y presione **"+ Nueva Auditoría"**.
2. Seleccione el almacén y la categoría a auditar.
3. El personal de almacén realiza el conteo a ciegas.
4. Al ingresar las cantidades físicas encontradas, el sistema calcula de inmediato las desviaciones (faltantes y sobrantes).
5. Al hacer clic en **"Aplicar Ajuste de Auditoría"**, el ERP ajusta los niveles de stock en la base de datos y genera el comprobante contable de pérdidas/ganancias por inventario.

---

## 7. Módulo de Compras y Proveedores

Gestiona la cadena de suministros, relaciones con proveedores y compras de reposición.

### 7.1. Directorio de Proveedores
* Registro completo: RIF, Razón Social, Contactos, Dirección Fiscal, Cuenta Bancaria para pagos y condición comercial (Contado / Crédito a X días).
* Historial de compras y evaluación de cumplimiento del proveedor.

### 7.2. Órdenes de Compra (PO)
1. Ingrese a **Compras > Órdenes de Compra** y presione **"+ Nueva Orden"**.
2. Elija el proveedor y el almacén receptor.
3. Agregue los productos a solicitar, cantidades y costos pactados en USD o Bs.
4. Guarde la orden en estado `PENDING` (Pendiente de Aprobación).
5. Un usuario con rol de compras o gerencia revisa y presiona **"Aprobar Orden"**.

### 7.3. Recepción de Mercancía y Factura de Proveedor
Cuando la mercancía física llega a las instalaciones:
1. Abra la Orden de Compra aprobada.
2. Haga clic en **"Recibir Mercancía"**.
3. Ingrese las cantidades efectivamente recibidas (permite recepciones parciales si el proveedor entregó solo una parte del pedido).
4. El inventario se incrementa de forma inmediata en el almacén indicado.
5. Ingrese el número de factura fiscal y número de control emitido por el proveedor.
6. Al confirmar:
   * Se genera automáticamente el registro en **Cuentas por Pagar (CxP)** con la fecha de vencimiento acordada.
   * La operación se envía al **Libro de Compras SENIAT**.
   * Se generan los comprobantes de retención de IVA e ISLR si la empresa es Agente de Retención Especial.

---

## 8. Módulo de Tesorería (CxC, CxP y Conciliación Bancaria)

Garantiza el control milimétrico de las entradas y salidas de dinero de la compañía.

### 8.1. Cuentas por Cobrar (CxC)
* **Consulta de Cartera:** Filtre por cliente, estado (Pendiente, Pagado Parcial, Vencido) y rango de fechas.
* **Registro de Cobro / Abono:**
  1. Ubique la factura a cobrar y presione **"Registrar Cobro"**.
  2. Ingrese el monto pagado por el cliente.
  3. Seleccione la cuenta bancaria de destino y el método (Transferencia, Pago Móvil, Zelle, Depósito en Cheque o Efectivo).
  4. Ingrese el número de referencia bancaria.
  5. Confirme. Se emite el Recibo de Cobro oficial y se reduce el saldo adeudado del cliente.

### 8.2. Cuentas por Pagar (CxP)
* Programe los pagos a proveedores según sus fechas de vencimiento para evitar morosidad y mantener un historial crediticio intachable.
* Registre egresos bancarios vinculados a las facturas de proveedores con deducción automática de saldos.

### 8.3. Reporte de Antigüedad de Saldos (Aging Report)
Reporte gerencial indispensable que clasifica las deudas de clientes y proveedores en tramos de tiempo:
* Corriente (Al día / Por vencer).
* 1 a 30 días de vencimiento.
* 31 a 60 días de vencimiento.
* 61 a 90 días de vencimiento.
* Más de 90 días (Cartera de alto riesgo o incobrable).

### 8.4. Conciliación Bancaria
* Permite cargar los extractos bancarios en formato digital (CSV o Excel de los principales bancos de Venezuela y cuentas internacionales).
* Cruce automático de transferencias y depósitos contra los cobros y pagos registrados en el ERP para detectar discrepancias bancarias o comisiones no contabilizadas.

---

## 9. Módulo Fiscal y Reportes SENIAT

Diseñado para dar cumplimiento estricto a las exigencias tributarias de la República Bolivariana de Venezuela (Providencias Administrativas vigentes del SENIAT).

### 9.1. Libro de Ventas Fiscal
* Acceda a **Fiscal > Libro de Ventas**.
* Seleccione el **Mes** y **Año** correspondiente a la declaración quincenal o mensual.
* El sistema presenta la matriz oficial normada:
  * Fecha de la factura.
  * Número de RIF y Nombre/Razón Social del comprador.
  * Número de Factura Fiscal.
  * Número de Control Fiscal.
  * Número de Nota de Débito o Crédito afectada.
  * Total Ventas Incluyendo IVA.
  * Ventas Exentas o Exoneradas.
  * Base Imponible General (16%) y Débito Fiscal generado.
  * Base Imponible Reducida (8%) y Adicional (si aplica).
  * Retenciones de IVA aplicadas por Clientes Especiales.
* **Exportación:** Descarga instantánea en formatos **Excel (.xlsx)** y **PDF** con membrete oficial listo para remitir al contador de la empresa.

### 9.2. Libro de Compras Fiscal
* Presenta todas las compras registradas con desglose de Base Imponible, Crédito Fiscal, IVA no deducible y retenciones de IVA efectuadas a proveedores.
* **Comprobante de Retención de IVA en PDF:** Genera e imprime el comprobante oficial de retención de IVA según la **Providencia Administrativa SNAT/2015/0049**, con correlativo de 14 dígitos (`AAAAMM00000001`), RIF del agente y sujeto retenido, alícuota legal (75% o 100%) y espacios para firma y sello húmedo.
* **Exportación de Archivo TXT para el Portal SENIAT:** Genera el archivo en texto plano tabulado (`AgentRIF\tPeriodo\tFecha\tC\t01\t...`) listo para ser cargado directamente en el portal fiscal del SENIAT en el módulo de Sujetos Pasivos Especiales.

---

## 10. Módulo de Nómina y Recursos Humanos (LOTTT Venezuela)

Nexus ERP integra un motor de nómina adaptado estrictamente a la **Ley Orgánica del Trabajo, los Trabajadores y las Trabajadoras (LOTTT)** y a los decretos presidenciales vigentes.

### 10.1. Expediente del Trabajador (Ficha Laboral)
* **Datos de Identificación:** Nombres, apellidos, Cédula de Identidad, RIF, teléfono, correo y dirección de habitación.
* **Condiciones Laborales:** Departamento, cargo, fecha de ingreso, frecuencia de cobro (Semanal / Quincenal / Mensual).
* **Compensación Bimonetaria:** Salario base pactado en USD y su equivalente en Bolívares según la tasa BCV oficial.
* **Cuentas Nómina:** Registro del banco y número de cuenta de 20 dígitos para dispersión bancaria.
* **Aplicabilidad de Leyes:** Casillas de verificación para activar/desactivar aportes de **S.S.O. (4%)**, **R.P.E. (0.5%)** y **F.A.O.V. (1%)**.

### 10.2. Cálculo Automatizado de Nómina Quincenal
* **Asignaciones Salariales:** Salario base de la quincena calculado en función del sueldo mensual.
* **Cestaticket Socialista:** Cálculo mensual y quincenal del beneficio de alimentación indexado a la tasa de cambio oficial.
* **Deducciones de Ley:**
  * **Seguro Social Obligatorio (IVSS):** 4% del salario mensual de los trabajadores.
  * **Régimen Prestacional de Empleo (RPE / Paro Forzoso):** 0.5% del salario mensual.
  * **Fondo de Ahorro Obligatorio para la Vivienda (BANAVIH / FAOV):** 1% del total devengado.
* **Total Neto:** Determinado en Bolívares y con contravalor referencial en Dólares ($ USD).

### 10.3. Recibos de Pago y Contabilización
* **Recibo Formal en PDF:** Emite el comprobante de pago individual para cada trabajador con detalle de haberes y deducciones, resumen neto y declaración de conformidad con firma y huella dactilar.
* **Cierre y Asiento Contable Automático:** Al cerrar la nómina, el sistema genera de forma autónoma el asiento en el Libro Diario contable debitando las cuentas de gasto de personal y acreditando las retenciones por enterar ante los organismos recaudadores (IVSS, BANAVIH) y los sueldos por pagar.

---

## 11. Módulo de Contabilidad General VEN-NIF

Nexus ERP cuenta con un motor contable automatizado que traduce cada operación comercial a partida doble.

### 10.1. Plan Único de Cuentas (Catálogo Contable)
* Estructura jerárquica multinivel (1. Activo, 2. Pasivo, 3. Patrimonio, 4. Ingresos, 5. Costos, 6. Gastos).
* Importación masiva del plan de cuentas desde plantilla estándar CSV.
* Creación y edición de cuentas auxiliares de detalle.

### 10.2. Asientos Contables Automáticos y Manuales
* **Modo Automático:** Cada vez que se confirma una venta, una compra o un pago en tesorería, el sistema genera de forma invisible el comprobante de diario correspondiente.
* **Asientos Manuales:** Para ajustes contables, depreciación de activos fijos, provisiones de nómina o amortizaciones.

### 10.3. Reportes Contables
* **Libro Diario y Libro Mayor.**
* **Balance de Comprobación de Sumas y Saldos.**
* **Balance General y Estado de Resultados (Pérdidas y Ganancias).**

---

## 12. Módulo de Configuración, Roles y Auditoría

### 12.1. Perfil de la Empresa y Sucursales
* Configuración del RIF, Razón Social, Dirección Fiscal, Teléfonos y Correo de Notificaciones.
* Carga del Logo Corporativo para documentos y facturas en PDF.
* Configuración de la tasa de cambio manual o enlace automático con la API del BCV.

### 12.2. Roles y Matriz de Permisos (RBAC)
El sistema incluye roles preconfigurados y permite crear roles personalizados combinando 23 permisos granulares:
* **Administrador del Sistema:** Acceso total y configuración.
* **Vendedor:** Emisión de cotizaciones y facturas, consulta de clientes y precios.
* **Cajero:** Operación de POS, cobros y cierre de turno de caja.
* **Almacenista:** Entradas, salidas, transferencias y auditorías físicas de stock.
* **Contador / Auditor:** Acceso a contabilidad, libros fiscales y reportes financieros sin permisos para alterar inventario operativo.

### 12.3. Bitácora de Auditoría (Audit Logs)
* Registro inmutable que almacena:
  * Fecha y hora exacta del evento.
  * Usuario responsable e IP de conexión.
  * Acción ejecutada (`CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `VOID`).
  * Módulo afectado e ID del registro.
  * Detalle de los datos anteriores y nuevos valores.

---

## 13. Preguntas Frecuentes (FAQ) y Soporte

**P: ¿Qué ocurre si la conexión a Internet se interrumpe mientras estoy facturando?**  
R: Las pantallas de venta y caja cuentan con protección contra duplicación de solicitudes. Si la conexión falla, no recargue la página inmediatamente; el sistema le avisará en pantalla el estado del documento y le permitirá reintentar de forma segura sin duplicar el descuento de inventario.

**P: ¿Cómo actualizo la tasa del dólar BCV en la mañana?**  
R: El sistema cuenta con un sincronizador automático que consulta la tasa oficial del BCV. Si desea fijar una tasa interna o ajustarla de emergencia, vaya a **Inventario > Tasa de Cambio**, ingrese el valor en Bolívares y presione "Actualizar Tasa". Todos los precios en Bolívares de todo el catálogo se recalcularán al instante en todo el ERP.

**P: ¿Puedo cambiar el formato de impresión de mis facturas al de mi impresora térmica de tickets?**  
R: Sí. En **Configuración > Facturación**, puede alternar entre el formato Carta (PDF estándar para hojas membretadas o impresoras láser) y el formato Ticket Térmico de 80mm o 58mm para impresoras de caja.

**P: ¿A quién acudo si necesito soporte técnico especializado?**  
R: Póngase en contacto con el equipo de soporte técnico de **Infagra Solution** a través de su canal corporativo o mediante el correo oficial de asistencia técnica.

---
*Manual Funcional de Usuario — Nexus ERP Enterprise © 2026 Infagra Solution. Todos los derechos reservados.*
