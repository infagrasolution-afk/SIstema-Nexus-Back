# 📑 PROPUESTA COMERCIAL Y CONTRATO DE LICENCIA DE SOFTWARE

## 🚀 APEX ERP: Ecosistema de Automatización Empresarial y Fiscal

**Empresa Desarrolladora:** InfaGraSolution  
**Director de Sistemas / Contacto Comercial:** Luis Infante  
**Teléfono / WhatsApp:** 0412-0161906  
**Correo Electrónico:** infagrasolution@gmail.com  
**Documento Nro:** IP-APEX-2026-001  
**Validez de la Propuesta:** 30 días  

---

### 1. CONCEPTO Y VISIÓN GENERAL
**APEX ERP** es una plataforma tecnológica SaaS de última generación desarrollada por **InfaGraSolution** que fusiona la flexibilidad y elegancia modular de **Odoo** con la robustez administrativo-contable y la adaptabilidad fiscal de **Profit Plus**, diseñada específicamente para el mercado de Venezuela.

Nuestra solución ofrece:
- **Aislamiento total de datos en la nube (PostgreSQL)** en servidores de alta disponibilidad.
- **Control fiscal y facturación adaptada al SENIAT** (impresoras fiscales HKA, Bematech, Aclas, o emisión en forma libre / manual de contingencia).
- **Punto de Venta (POS) táctil** de alta velocidad con capacidad de contingencia offline y compatibilidad con impresoras térmicas (58mm y 80mm) y lectores de códigos de barra (EAN/UPC).
- **Control de Inventarios Multi-Almacén:** Gestión del Depósito Principal y depósitos externos, control de stock mínimo con alarmas dinámicas de reposición, transferencias, notas de despacho, auditorías físicas y productos a granel con decimales (kg, gr, mt, lt).
- **Multi-moneda nativa:** Precios fijados en dólares ($ USD) con conversión automática a Bolívares (Bs.) según la tasa oficial del Banco Central de Venezuela (BCV).
- **Visualización simultánea:** Operación en tiempo real tanto en la computadora de ventas (caja/mostrador) como en las computadoras de la oficina (administración/almacén).

---

### 2. CATÁLOGO DE MÓDULOS DISPONIBLES (Selección de Licencia)
*Marque con una equis `[X]` los módulos incluidos en esta contratación:*

#### `[X]` MÓDULO BASE OBLIGATORIO: ADMINISTRATIVO + GESTIÓN DE INVENTARIOS & ALMACÉN (WMS)
*(Se comercializan juntos como el núcleo operativo indispensable del sistema)*
- **Gestión Multi-Almacén:** Control independiente para Depósito Principal y 2 o más Depósitos Externos.
- **Catálogo de Productos:** SKU único, código de barras EAN/UPC, categoría, imagen/foto del producto y margen de ganancia.
- **Control de Stock Mínimo (Alarma de Stop):** Alertas visuales dinámicas para prevenir quiebres de inventario.
- **Soporte de Productos a Granel:** Manejo de cantidades con precisión de hasta 4 decimales (`1.500 kg`, `0.250 kg`).
- **Ubicación Física de Mercancía:** Pasillos, estantes, casilleros (Bin Locations) e impresión de etiquetas QR.
- **Operaciones de Inventario:** Cargos (entradas), Descargos (salidas, mermas), Ajustes y Auditorías Físicas (conteo ciego vs teórico).
- **Cálculo de Costo Promedio Ponderado** automático con cada recepción.
- **Directorio de Clientes y Proveedores:** Registro con RIF/Cédula, dirección, teléfonos y límites crediticios.
- **Notas de Entrega y Despacho:** Emisión de notas de entrega para clientes y notas de despacho entre depósitos en PDF.
- **Facturación en Forma Libre:** Facturación manual de contingencia.
- **Multi-moneda y Tasa BCV:** Fijación de precios en USD con conversión automática a Bolívares a tasa oficial.

#### `[ ]` MÓDULO ADICIONAL 1: PUNTO DE VENTA INTELIGENTE (POS) & GESTIÓN DE CAJA
- Interfaz POS táctil de alta velocidad optimizada para facturación rápida en mostrador.
- Búsqueda instantánea por lector de código de barras USB/Bluetooth o teclado.
- Gestión de Sesiones de Caja: Aperturas de caja con saldo inicial, cierres y arqueos con conteo de efectivo y reporte de diferencias.
- Soporte multimoneda: Gestión de cobros en Bolívares (Efectivo, Pago Móvil, Punto de Venta) y Divisas (USD Efectivo, Zelle).
- Cálculo automatizado de vueltos y cambio en tiempo real.
- Compatibilidad con impresoras térmicas de 58mm y 80mm.

#### `[ ]` MÓDULO ADICIONAL 2: CONECTOR FISCAL APEX (AGENTE SENIAT LOCAL)
- Integración física con Impresoras Fiscales homologadas en Venezuela (**The Factory HKA, Bematech, Aclas**).
- Agente local autónomo en puerto `8080`.
- Sistema de **Bypass de Emergencia:** Facturación digital o libre en contingencia si la impresora fiscal presenta fallas mecánicas o desconexión.
- Monitoreo en tiempo real del estado de la impresora (🟢 Activo / 🔴 Desconectado).

#### `[ ]` MÓDULO ADICIONAL 3: TESORERÍA (CUENTAS POR COBRAR Y POR PAGAR)
- **Cuentas por Cobrar (CxC):** Control de cartera de crédito de clientes, límites asignados, registro de abonos parciales y totales en USD o Bs.
- **Cuentas por Pagar (CxP):** Programación y control de pagos a proveedores derivados de órdenes de compra.
- **Gestión Bancaria:** Conciliación bancaria, registro de cuentas corrientes, ahorro y en divisas.
- Reporte automatizado de antigüedad de saldos.

#### `[ ]` MÓDULO ADICIONAL 4: GESTIÓN DE COMPRAS & PROVEEDORES
- Creación y seguimiento de Órdenes de Compra.
- Recepción de insumos y mercancía en almacén con incremento automático de existencias.
- Aplicación de retenciones fiscales de IVA (75%) e ISLR.
- Actualización automática del costo de catálogo.

#### `[ ]` MÓDULO ADICIONAL 5: CONTABILIDAD AUXILIAR & LIBROS FISCALES SENIAT
- Generación y exportación de **Libros de Compras y Ventas** con especificaciones SENIAT (Providencia 0049).
- Creación automática de asientos de diario contables basados en las operaciones del POS y facturación.
- Plan de Cuentas dinámico adaptable a la providencia fiscal venezolana.
- Cálculo de retenciones y soporte para el **IGTF (Impuesto a las Grandes Transacciones Financieras - 3%)**.

#### `[ ]` MÓDULO ADICIONAL 6: NÓMINA & GESTIÓN DE TALENTO HUMANO (LOTTT)
- Expediente digital de trabajadores y control de contratos.
- Cálculo de salarios quincenales y mensuales bajo normativa venezolana (IVSS, FAOV, INCES).
- Control de horas extras, bonos y deducciones.
- Generación de recibos de pago formales en formato PDF.

---

### 3. ESQUEMA DE INVERSIÓN Y LICENCIA OFICIAL

El licenciamiento de **APEX ERP** opera bajo un esquema transparente donde la inversión del primer año incluye el aprovisionamiento de infraestructura en la nube dedicada, configuración inicial y la licencia por 1 año (365 días).

| Concepto de Módulo / Servicio | Frecuencia | Inversión Inicial (Año 1) | Renovación Anual (Año 2+) | Seleccionado |
| :--- | :---: | :---: | :---: | :---: |
| **MÓDULO BASE OBLIGATORIO:**<br/>Administrativo + Inventario & Almacén (WMS)<br/>*(Incluye aprovisionamiento PostgreSQL en la nube, setup y 1 año de licencia)* | Anual | **$700.00 USD** | **$400.00 USD** | `[X]` |
| **Punto de Venta (POS) & Conector Fiscal** | Anual | **$350.00 USD** | **$250.00 USD** | `[ ]` |
| **Tesorería (Cuentas por Cobrar & Cuentas por Pagar, Bancos)** | Anual | **$350.00 USD** | **$250.00 USD** | `[ ]` |
| **Gestión de Compras & Costeo Ponderado** | Anual | **$350.00 USD** | **$250.00 USD** | `[ ]` |
| **Contabilidad Auxiliar & Libros SENIAT** | Anual | **$350.00 USD** | **$250.00 USD** | `[ ]` |
| **Nómina y Recursos Humanos (LOTTT)** | Anual | **$350.00 USD** | **$250.00 USD** | `[ ]` |

#### Resumen Financiero:
- **Subtotal Inversión Año 1:** $___________ USD
- **Descuento Promocional / Precio Especial Acordado:** -$___________ USD
- **Total Neto a Pagar Año 1:** $___________ USD *(Equivalente a Bs. ___________ a Tasa Oficial BCV)*
- **Costo de Renovación Anual Futura (a partir del Año 2):** $___________ USD / año

#### Acuerdos Especiales y Condiciones de Pago:
____________________________________________________________________________________________________  
____________________________________________________________________________________________________  
____________________________________________________________________________________________________  

**Moneda de Pago:** Divisas USD (Efectivo / Transferencia / Zelle) o en Bolívares (Tasa oficial BCV a la fecha de pago).  

---

### 4. ACUERDOS DE NIVEL DE SERVICIO (SLA) & RESPONSABILIDADES
1. **Disponibilidad:** El sistema estará alojado en servidores en la nube de alta disponibilidad, garantizando un **99.9% de uptime** operativo.
2. **Copias de Seguridad (Backups):** Se realizarán respaldos automatizados diarios de la base de datos de forma totalmente aislada para asegurar la continuidad del negocio.
3. **Soporte Técnico:** Soporte prioritario vía WhatsApp (**0412-0161906**) y correo (**infagrasolution@gmail.com**) en horario comercial para la atención de incidentes urgentes en el POS y la comunicación fiscal.
4. **Propiedad Intelectual:** La licencia otorga el derecho de uso de la plataforma APEX ERP por el periodo contratado.

### 5. GARANTÍA DE CONTINUIDAD DE SERVICIO Y PROPIEDAD DE DATOS
1. **Propiedad Absoluta de la Información:** Todos los datos registrados en el sistema (clientes, productos, ventas, inventarios, transacciones contables y logs) pertenecen única y exclusivamente al **Cliente**. **InfaGraSolution** no podrá restringir el acceso o la descarga de dicha información bajo ningún concepto.
2. **Portabilidad y Descarga de Resguardos:** El **Cliente** tiene la facultad en cualquier momento de exportar y descargar resguardos completos de sus inventarios, facturas y libros fiscales en formatos abiertos (CSV y Excel).
3. **Escrow de Código Fuente (Garantía de Supervivencia):** En caso de cese de operaciones definitivo del **Proveedor (InfaGraSolution)**, se otorgará al **Cliente** una licencia perpetua sin costo y se le facilitará una copia ejecutable del sistema y su base de datos PostgreSQL para su despliegue independiente.

---

### 6. DECLARACIÓN DE CONFORMIDAD Y FIRMAS

Al firmar este documento, el **Cliente** y el **Proveedor (InfaGraSolution)** declaran aceptar las condiciones de licenciamiento, el esquema de costos arriba detallados y los módulos seleccionados para la puesta en marcha de la suite **APEX ERP**.

Se firma por duplicado y de conformidad a los ______ días del mes de ________________ del año 2026.

<br/>

| **POR EL PROVEEDOR** | **POR EL CLIENTE** |
| :--- | :--- |
| **Firma:** ________________________________ | **Firma:** ________________________________ |
| **Nombre:** Luis Infante | **Nombre:** ______________________________ |
| **Cargo:** Director de Sistemas / Representante Comercial | **Cargo:** Representante Legal / Propietario |
| **Teléfono:** 0412-0161906 | **Teléfono:** ____________________________ |
| **Correo:** infagrasolution@gmail.com | **Correo:** ______________________________ |
| **Empresa:** InfaGraSolution | **Empresa:** ______________________________ |

<br/>

---
*Documento emitido por el sistema de licenciamiento y control comercial de InfaGraSolution · APEX ERP.*
