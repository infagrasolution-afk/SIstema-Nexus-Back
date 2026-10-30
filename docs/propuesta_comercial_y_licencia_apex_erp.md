# 📑 PROPUESTA COMERCIAL Y CONTRATO DE LICENCIA DE SOFTWARE

## 🚀 APEX ERP: Ecosistema de Automatización Empresarial y Fiscal

**Proveedor:** Infagrasolution  
**Fecha de Emisión:** 1 de Junio de 2026  
**Documento Nro:** IP-APEX-2026-001  
**Validez de la Propuesta:** 30 días  

---

### 1. CONCEPTO Y VISIÓN GENERAL
**APEX ERP** es una plataforma tecnológica SaaS de última generación que fusiona la flexibilidad y elegancia modular de **Odoo** con la robustez administrativo-contable y la adaptabilidad fiscal de **Profit Plus**, diseñada específicamente para el mercado de Venezuela.

Nuestra solución ofrece aislamiento total de datos en la nube (PostgreSQL), control fiscal integrado con el SENIAT, un punto de venta (POS) de alta velocidad con capacidad de contingencia offline, y auditoría inmutable basada en logs seguros.

---

### 2. CATÁLOGO DE MÓDULOS DISPONIBLES (Selección de Licencia)
*Marque con una equis `[X]` los módulos adquiridos en esta contratación:*

#### `[ ]` MÓDULO 1: PUNTO DE VENTA INTELIGENTE (POS) & GESTIÓN DE CAJA
- Interfaz POS táctil de alta velocidad optimizada para facturación rápida.
- Gestión de Sesiones de Caja (Aperturas, Cierres, Arqueos de Caja con conteo de efectivo y reporte de diferencias).
- Soporte multimoneda (Gestión en Bolívares y Divisas).
- Cálculo automatizado y visualización de vueltos en tiempo real.
- Registro automático de cajeros por UID físico del computador.

#### `[ ]` MÓDULO 2: CONECTOR FISCAL APEX (AGENTE SENIAT LOCAL)
- Integración física con Impresoras Fiscales homologadas en Venezuela (**The Factory HKA, Bematech, Aclas**).
- Agente local autónomo (`nexus-fiscal-connector.exe` local en puerto `8080`).
- Sistema de **Bypass de Emergencia:** Facturación digital o libre en contingencia si la impresora fiscal presenta fallas mecánicas o desconexión.
- Monitoreo en tiempo real del estado de la impresora (🟢 Activo / 🔴 Desconectado).

#### `[ ]` MÓDULO 3: GESTIÓN DE INVENTARIOS & ALMACÉN (WMS)
- Control de stock por almacenes y sucursales con SKU único y códigos de barra.
- Operaciones de Ajuste Manual: **Cargos** (Inventario Inicial, Entradas) y **Descargos** (Salidas, Mermas).
- Cálculo automático de **Costo Promedio Ponderado** en cada entrada.
- Alertas dinámicas de Stock Mínimo y reposición de mercancía.
- Generación de Notas de Entrega corporativas con formato PDF para despachos.

#### `[ ]` MÓDULO 4: TESORERÍA (CUENTAS POR COBRAR Y PAGAR)
- Módulo de CxC para control de crédito a clientes e historial de pagos.
- Módulo de CxP para administración de compromisos de pago con proveedores.
- Registro detallado de amortizaciones y facturas pendientes.
- Reporte automatizado de antigüedad de saldos.

#### `[ ]` MÓDULO 5: CONTABILIDAD AUXILIAR & LIBROS FISCALES
- Generación y exportación de **Libros de Compras y Ventas** con especificaciones SENIAT.
- Creación automática de asientos de diario contables basados en las transacciones del POS.
- Plan de Cuentas dinámico adaptable a la providencia fiscal venezolana.
- Cálculo de retenciones y soporte para el **IGTF (Impuesto a las Grandes Transacciones Financieras - 3%)**.

#### `[ ]` MÓDULO 6: ADMINISTRACIÓN MULTI-TENANT (SAAS CONTROL)
- Consola Master para superusuarios para administrar múltiples sub-empresas (Inquilinos/Tenants).
- Control de Licenciamiento individual por inquilino (**Demo, Activa, Master**).
- Panel de personalización estética: logotipo de empresa, colores corporativos y datos de identificación (RIF, Dirección).
- Bitácora de Auditoría inmutable para el rastreo de operaciones sensibles por usuario.

---

### 3. ESQUEMA DE INVERSIÓN Y LICENCIA

| Concepto de Servicio | Frecuencia | Costo (USD) | Seleccionado |
| :--- | :--- | :--- | :---: |
| **Instalación y Configuración Inicial** (Base de datos e inicialización en la nube) | Pago Único | $___________ | `[ ]` |
| **Licencia de Uso Mensual APEX ERP** (Suscripción recurrente en la nube) | Mensual | $___________ | `[ ]` |
| **Licencia Anual APEX ERP** (Descuento especial por suscripción anual) | Anual | $___________ | `[ ]` |
| **Soporte Técnico Premium & Actualizaciones Fiscales** (Monitoreo de Render + SLA) | Mensual | $___________ | `[ ]` |
| **Integración e Inducción de Impresoras Fiscales** (Por cada terminal fiscal) | Pago Único | $___________ | `[ ]` |

**Moneda de Pago:** Divisas USD (Efectivo / Transferencia) o en Bolívares (Tasa oficial BCV a la fecha de pago).  
**Día de Facturación Mensual:** ______ de cada mes.

---

### 4. ACUERDOS DE NIVEL DE SERVICIO (SLA) & RESPONSABILIDADES
1. **Disponibilidad:** El sistema estará alojado en servidores en la nube de alta disponibilidad (Render con base de datos PostgreSQL), garantizando un **99.9% de uptime** operativo.
2. **Copias de Seguridad (Backups):** Se realizarán respaldos automatizados diarios de las bases de datos de cada inquilino de forma totalmente aislada para asegurar la continuidad del negocio.
3. **Soporte Técnico:** Soporte prioritario vía WhatsApp en horario comercial para la atención de incidentes urgentes en el POS y la comunicación fiscal.
4. **Propiedad Intelectual:** La licencia otorga el derecho de uso de la plataforma APEX ERP por el periodo contratado. El cliente se compromete a no sublicenciar, revender o realizar ingeniería inversa del código fuente del backend o frontend.

### 5. GARANTÍA DE CONTINUIDAD DE SERVICIO Y PROPIEDAD DE DATOS
Para la tranquilidad comercial y legal del **Cliente**, se establecen las siguientes garantías de continuidad operativa y resguardo de información sobre el alojamiento en la nube:

1. **Propiedad Absoluta de la Información:** Todos los datos registrados en el sistema (clientes, productos, ventas, inventarios, transacciones contables y logs) pertenecen única y exclusivamente al **Cliente**. El **Proveedor** no podrá restringir el acceso o la descarga de dicha información bajo ningún concepto.
2. **Portabilidad y Descarga de Resguardos:** El **Cliente** tiene la facultad en cualquier momento, desde el panel administrativo, de descargar resguardos completos de sus inventarios, facturas y libros fiscales en formatos abiertos e independientes (como CSV y Excel), garantizando que su historial comercial no esté atado al sistema.
3. **Escrow de Código Fuente (Garantía de Supervivencia):** En caso de cese de operaciones definitivo, disolución comercial o quiebra del **Proveedor (Infagrasolution)**, se otorgará al **Cliente** una licencia perpetua sin costo de uso y se le entregará una copia del código fuente ejecutable del backend, el frontend y la estructura de su base de datos PostgreSQL, permitiéndole desplegar su propia instancia en un servidor local o en la nube que decida contratar de forma independiente.
4. **Respaldos Geo-Replicados:** Los datos se encuentran replicados de forma segura en múltiples servidores en la nube de Render (con infraestructura AWS), asegurando que cualquier catástrofe física en un centro de datos no representará la pérdida de la información histórica de la empresa.

---

### 6. DECLARACIÓN DE CONFORMIDAD Y FIRMAS

Al firmar este documento, el **Cliente** y el **Proveedor (Infagrasolution)** declaran aceptar las condiciones de licenciamiento, el esquema de costos arriba detallados y los módulos seleccionados para la puesta en marcha de la suite **APEX ERP**.

Se firma por duplicado y de conformidad a los ______ días del mes de ________________ del año 2026.

<br/>

| **POR EL PROVEEDOR** | **POR EL CLIENTE** |
| :--- | :--- |
| **Firma:** ________________________________ | **Firma:** ________________________________ |
| **Nombre:** ______________________________ | **Nombre:** ______________________________ |
| **Cargo:** Representante Técnico / Comercial | **Cargo:** Representante Legal / Propietario |
| **RIF / C.I.:** ____________________________ | **RIF / C.I.:** ____________________________ |
| **Empresa:** Infagrasolution | **Empresa:** ______________________________ |

<br/>

---
*Documento emitido por el sistema de licenciamiento y control comercial de APEX ERP.*
