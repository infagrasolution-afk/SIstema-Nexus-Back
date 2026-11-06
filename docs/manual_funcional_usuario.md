# 📘 Manual Funcional de Usuario Oficial — APEX ERP

> **Desarrollado por:** InfaGraSolution  
> **Director de Sistemas / Soporte:** Luis Infante  
> **Teléfono / WhatsApp:** 0412-0161906  
> **Correo Electrónico:** infagrasolution@gmail.com  
> **Versión:** 2.0 Enterprise Cloud · Sistema Multi-Tenant Adaptado a Venezuela  

---

## 📑 Tabla de Contenidos

1. [Visión General y Arquitectura del Sistema](#1-visión-general-y-arquitectura-del-sistema)
2. [Acceso, Autenticación y Seguridad](#2-acceso-autenticación-y-seguridad)
3. [Panel de Control (Dashboard) y Métricas en Tiempo Real](#3-panel-de-control-dashboard-y-métricas-en-tiempo-real)
4. [Gestión de Inventario y Almacenes (WMS)](#4-gestión-de-inventario-y-almacenes-wms)
   - 4.1. Catálogo de Productos y Registro con Fotos
   - 4.2. Control de Stock Mínimo (Alarma de Stop)
   - 4.3. Productos a Granel (Pesaje y Fracciones Decimales)
   - 4.4. Manejo Multi-Almacén y Depósitos Externos
   - 4.5. Ubicación Física de Mercancía (Bin Locations) y Etiquetas QR
   - 4.6. Operaciones: Cargos, Descargos y Ajustes de Inventario
   - 4.7. Transferencias entre Depósitos y Notas de Despacho
   - 4.8. Auditorías Físicas de Inventario (Conteo Ciego vs. Teórico)
   - 4.9. Costo Promedio Ponderado
   - 4.10. Carga e Importación Masiva mediante Archivos CSV
5. [Ventas, Facturación y Punto de Venta (POS)](#5-ventas-facturación-y-punto-de-venta-pos)
   - 5.1. Directorio de Clientes y Políticas de Crédito
   - 5.2. Terminal de Punto de Venta (POS) Táctil
   - 5.3. Gestión de Caja: Aperturas, Cierres y Arqueos
   - 5.4. Lector de Códigos de Barra e Impresoras Térmicas (58mm / 80mm)
   - 5.5. Conector Fiscal SENIAT e Impresoras Fiscales Homologadas
   - 5.6. Facturación Manual y en Forma Libre (Contingencia)
   - 5.7. Notas de Entrega a Clientes en PDF
   - 5.8. Presupuestos y Cotizaciones
   - 5.9. Notas de Crédito y Débito
6. [Módulo de Compras y Proveedores](#6-módulo-de-compras-y-proveedores)
   - 6.1. Directorio de Proveedores y Agentes de Retención
   - 6.2. Órdenes de Compra y Recepción en Depósitos
   - 6.3. Retenciones de IVA (75%) e ISLR
7. [Tesorería y Finanzas](#7-tesorería-y-finanzas)
   - 7.1. Cuentas por Cobrar (CxC)
   - 7.2. Cuentas por Pagar (CxP)
   - 7.3. Cuentas Bancarias y Conciliación
   - 7.4. Caja Chica y Movimientos de Tesorería
8. [Módulo Fiscal y Reportes SENIAT](#8-módulo-fiscal-y-reportes-seniat)
   - 8.1. Libros Oficiales de Compras y Ventas (Providencia 0049)
   - 8.2. Impuesto a las Grandes Transacciones Financieras (IGTF 3%)
9. [Módulo Contable Auxiliar (VEN-NIF)](#9-módulo-contable-auxiliar-ven-nif)
10. [Nómina y Gestión de Talento Humano (LOTTT)](#10-nómina-y-gestión-de-talento-humano-lottt)
11. [Panel de Súper Administrador SaaS y Cotizador de Licencias](#11-panel-de-súper-administrador-saas-y-cotizador-de-licencias)
12. [Preguntas Frecuentes (FAQ) y Soporte Técnico InfaGraSolution](#12-preguntas-frecuentes-faq-y-soporte-técnico-infagrasolution)

---

## 1. Visión General y Arquitectura del Sistema

**APEX ERP** es un ecosistema tecnológico integral diseñado por **InfaGraSolution** para resolver las necesidades operativas, comerciales y fiscales de las empresas en Venezuela.

### Principales Ventajas Arquitectónicas:
1. **Aislamiento Multi-Tenant:** Cada empresa cliente posee su propia base de datos dedicada y aislada en PostgreSQL en la nube, garantizando absoluta privacidad y seguridad.
2. **Visualización Simultánea (Ventas y Oficina):** Arquitectura cliente-servidor web en tiempo real. La computadora de ventas (mostrador/POS) y las computadoras administrativas de la oficina (gerencia, compras, almacén) acceden simultáneamente sin interferencias ni bloqueos.
3. **Moneda Dual Nativa (USD / Bs. BCV):** Los precios de catálogo se fijan en dólares ($ USD) para proteger el valor de la mercancía. El sistema consulta y sincroniza automáticamente la tasa del **Banco Central de Venezuela (BCV)**, efectuando la conversión a Bolívares en tiempo real.
4. **Soporte Físico y Online:** Funciona alojado en servidores en la nube de alta disponibilidad (99.9% uptime) y cuenta con mecanismos de contingencia local para impresión de tickets térmicos o fiscales mediante un agente local en puerto `8080`.

---

## 2. Acceso, Autenticación y Seguridad

### 2.1. Inicio de Sesión
1. Abra su navegador web (Google Chrome, Mozilla Firefox o Microsoft Edge recomendados) e ingrese la URL proporcionada para su empresa.
2. Ingrese su **Nombre de Usuario** o **Correo Electrónico**.
3. Ingrese su **Contraseña**.
4. Presione el botón **Iniciar Sesión**.
5. Al ingresar por primera vez, el sistema ejecutará el **Asistente Guiado (System Wizard)** que le enseñará la ubicación de los módulos clave.

### 2.2. Políticas de Seguridad y Bloqueo de Cuentas
* **Intentos Fallidos:** Se permiten hasta 3 intentos fallidos consecutivos de contraseña.
* **Bloqueo Preventivo:** Al tercer intento incorrecto, la cuenta se bloquea automáticamente para repeler ataques de fuerza bruta.
* **Desbloqueo de Usuarios:** El Administrador de la empresa puede desbloquear usuarios desde la pantalla **Administración > Usuarios**.
* **Bloqueo del Administrador Principal:** En caso de que la cuenta administradora se bloquee, contacte de inmediato a **InfaGraSolution (Luis Infante al 0412-0161906 o infagrasolution@gmail.com)** para su restablecimiento seguro.

### 2.3. Cierre de Sesión Automático por Inactividad
Por regulaciones bancarias y de resguardo comercial, el sistema detecta períodos prolongados de inactividad (sin movimiento de mouse o teclado) y cerrará la sesión de forma segura para evitar que personal no autorizado acceda a la computadora si queda desatendida.

---

## 3. Panel de Control (Dashboard) y Métricas en Tiempo Real

El Dashboard es el centro de mando del ERP. Al ingresar, presenta métricas operativas al instante:
* **Total Facturado en el Mes:** Consolidado de ventas brutas en USD y su equivalente en Bs. a tasa BCV.
* **Cobranzas Recaudadas:** Monto total percibido en caja y cuentas bancarias.
* **Cuentas por Cobrar Pendientes (CxC):** Cartera pendiente de clientes clasificada por estado.
* **Cuentas por Pagar (CxP):** Compromisos inmediatos con proveedores.
* **Valorización Total del Inventario:** Valuación monetaria en tiempo real a costo promedio ponderado.
* **Alertas de Stock Mínimo:** Lista de productos que requieren reposición inmediata.

---

## 4. Gestión de Inventario y Almacenes (WMS)

El módulo de inventario controla el ciclo de vida de la mercancía, desde la recepción hasta el despacho.

### 4.1. Catálogo de Productos y Registro con Fotos
1. Ingrese a **Inventario > Catálogo de Productos**.
2. Presione el botón **+ Nuevo Producto**.
3. Complete los datos de la ficha:
   - **SKU (Código Único):** Código interno de identificación.
   - **Código de Barras:** Código EAN-13, UPC o código interno para escaneo con lector.
   - **Nombre y Descripción Detallada:** Nombre comercial y características.
   - **Categoría:** Departamento o línea del producto.
   - **Foto del Producto:** Suba la imagen del producto para su previsualización en catálogo y POS.
   - **Precio de Venta (USD):** Precio base en divisas.
   - **Costo Base (USD):** Costo de adquisición.
   - **Margen de Ganancia (%):** Margen comercial calculado.
   - **Tasa de IVA:** Seleccione 16%, 8% o Exento.

### 4.2. Control de Stock Mínimo (Alarma de Stop)
* En la ficha del producto configure el campo **Stock Mínimo**.
* **Comportamiento:** Cuando la existencia física en almacén sea menor o igual al stock mínimo, el sistema activará una **Alarma Visual de Reposición** en el Dashboard y en el módulo de inventario para que el departamento de compras reponga mercancía antes de que ocurra un quiebre de stock.

### 4.3. Productos a Granel (Pesaje y Fracciones Decimales)
* En el campo **Unidad de Medida**, seleccione la unidad correspondiente: `kg` (kilogramos), `gr` (gramos), `mt` (metros), `lt` (litros) o `unit` (unidad).
* Las cantidades se procesan con **precisión financiera de hasta 4 decimales** (`Numeric(18, 4)`). Esto permite registrar ventas como `1.750 kg`, `0.325 kg` o despachar fracciones exactas de mercancía pesada en balanza.

### 4.4. Manejo Multi-Almacén y Depósitos Externos
* El sistema permite operar con múltiples bodegas físicas:
  1. Diríjase a **Inventario > Almacenes y Ubicaciones**.
  2. Cree el **Depósito Principal** y tantos **Depósitos Externos** como posea su empresa (ej. Depósito Externo 1, Depósito Externo 2, Almacén de Tránsito).
  3. Cada depósito mantiene su conteo de existencias de manera completamente independiente.

### 4.5. Ubicación Física de Mercancía (Bin Locations) y Etiquetas QR
* Dentro de cada almacén, organice el espacio físico creando ubicaciones tipo:  
  `Pasillo - Estante - Tramo/Casillero` (ejemplo: `A1-S2-B3`).
* Presione el botón **Imprimir Etiqueta QR** para generar e imprimir la etiqueta física con código QR y adherirla al estante.

### 4.6. Operaciones: Cargos, Descargos y Ajustes de Inventario
* **Cargos (Entradas Manuales):** Utilizado para ingresar saldos iniciales de inventario o ingresos no asociados a una compra.
* **Descargos (Salidas Manuales / Mermas):** Utilizado para dar de baja mercancía dañada, vencida, mermas o autoconsumo, justificando el motivo en el campo observaciones.
* **Ajustes:** Permite corregir discrepancias entre el inventario del sistema y la realidad física.

### 4.7. Transferencias entre Depósitos y Notas de Despacho
1. Diríjase a **Inventario > Transferencias**.
2. Seleccione el **Almacén Origen** y el **Almacén Destino**.
3. Agregue los productos y cantidades a trasladar.
4. Al confirmar, el sistema descuenta del origen, incrementa en el destino y permite emitir e imprimir la **Nota de Despacho oficial en PDF** para el transportista.

### 4.8. Auditorías Físicas de Inventario (Conteo Ciego vs. Teórico)
1. Ingrese a **Inventario > Auditoría Física**.
2. Cree una nueva auditoría seleccionando el depósito a inspeccionar.
3. El personal realiza el conteo físico en sitio e ingresa las cantidades contadas.
4. El sistema compara el conteo contra el stock teórico y genera un informe de diferencias (sobrantes y faltantes) para su aprobación gerencial.

### 4.9. Costo Promedio Ponderado
Con cada orden de compra recibida a un costo diferente, el sistema recalcula automáticamente el **Costo Promedio Ponderado** bajo la fórmula:
$$\text{Nuevo Costo} = \frac{(\text{Stock Actual} \times \text{Costo Actual}) + (\text{Cantidad Entrante} \times \text{Costo Entrante})}{\text{Stock Total Resultante}}$$

### 4.10. Carga e Importación Masiva mediante Archivos CSV
1. En **Inventario > Catálogo**, presione **Importar Cargo Inicial**.
2. Descargue la plantilla oficial en formato CSV.
3. Complete los datos en Excel (sin alterar los nombres de las columnas) y guarde como archivo `.csv`.
4. Cargue el archivo en el sistema para dar de alta miles de productos e inventarios en segundos.

---

## 5. Ventas, Facturación y Punto de Venta (POS)

### 5.1. Directorio de Clientes y Políticas de Crédito
* Registre clientes en **Ventas > Clientes** con su RIF/Cédula, nombre, teléfono, dirección y correo.
* Configure el **Límite de Crédito en USD** y los **Días de Crédito** (ej. 15 o 30 días). Si el cliente excede su límite o tiene facturas vencidas, el sistema alertará al facturador.

### 5.2. Terminal de Punto de Venta (POS) Táctil
* Diseñado para máxima velocidad en mostrador.
* Búsqueda ágil: Pase el producto por el **lector de códigos de barra**, o búsquelo por nombre o SKU.
* Botonera táctil con teclado numérico integrado.
* Registro de clientes recurrentes o selección rápida de "Consumidor Final".

### 5.3. Gestión de Caja: Aperturas, Cierres y Arqueos
1. **Apertura de Turno:** Al iniciar el día, el cajero debe registrar el fondo inicial de caja en Bolívares y en Dólares.
2. **Cobros Multimoneda:** En la pantalla de pago se pueden ingresar pagos combinados:
   - Dólares en efectivo
   - Bolívares en efectivo
   - Pago Móvil
   - Punto de Venta / Tarjetas de Débito
   - Transferencia bancaria o Zelle
   - Venta a crédito
3. **Cálculo de Cambio / Vueltos:** El sistema calcula de inmediato el vuelto exacto a entregar tanto en divisas como en bolívares.
4. **Cierre de Caja y Arqueo:** Al finalizar el turno, el cajero ingresa el conteo ciego de dinero físico. El sistema genera el **Reporte de Arqueo** comparando el dinero real contra las ventas registradas, indicando si el cuadre fue exacto o si existe sobrante o faltante.

### 5.4. Lector de Códigos de Barra e Impresoras Térmicas
* **Lectores de Códigos de Barra:** Compatible con cualquier lector USB o Bluetooth Plug & Play.
* **Impresoras Térmicas:** Emisión de tickets térmicos en formatos estándar de **58mm y 80mm** con desglose bimonetario (USD / Bs. BCV).

### 5.5. Conector Fiscal SENIAT e Impresoras Fiscales Homologadas
* Compatible con impresoras fiscales venezolanas homologadas (**The Factory HKA, Bematech, Aclas**).
* Funciona mediante el agente local en puerto `8080`.
* Registra el número de factura fiscal, número de control SENIAT y serial de la impresora en cada venta.
* **Bypass de Contingencia:** Si la impresora fiscal presenta atasco de papel o desconexión, el sistema permite facturar en formato libre de contingencia para no detener la operación comercial.

### 5.6. Facturación Manual y en Forma Libre (Contingencia)
* Ubicado en **Ventas > Facturación Manual**. Permite emitir facturas en formato libre pre-impreso o digital cumpliendo los datos fiscales exigidos.

### 5.7. Notas de Entrega a Clientes en PDF
1. Diríjase a **Ventas > Notas de Entrega**.
2. Presione **+ Nueva Nota de Entrega**, seleccione el cliente, los productos y la dirección de despacho.
3. Presione el botón **Descargar / Imprimir (PDF)** para obtener el documento formal con logotipo de la empresa, correlativo oficial y líneas de firma de entrega y recepción.

### 5.8. Presupuestos y Cotizaciones
* En **Ventas > Presupuestos**, emita cotizaciones comerciales con tiempo de validez determinado.
* Cuando el cliente apruebe la cotización, con un solo clic el presupuesto se convierte en una venta sin necesidad de volver a transcribir los ítems.

### 5.9. Notas de Crédito y Débito
* Módulo en **Ventas > Notas de Crédito** para procesar devoluciones de mercancía y ajustes de precios, con opción de reintegrar automáticamente los productos devueltos al almacén seleccionado.

---

## 6. Módulo de Compras y Proveedores

### 6.1. Directorio de Proveedores y Agentes de Retención
* Registro en **Compras > Proveedores**: RIF, razón social, teléfonos, persona de contacto, cuentas bancarias e indicación de si el proveedor es agente de retención.

### 6.2. Órdenes de Compra y Recepción en Depósitos
1. Genere la orden de compra en **Compras > Órdenes de Compra**.
2. Al recibir la mercancía, presione **Recibir Mercancía**, seleccione el almacén destino (Depósito Principal o Depósito Externo) e ingrese el número de factura y control del proveedor.
3. El sistema actualiza el stock, recalcula el costo promedio ponderado y genera la cuenta por pagar (CxP).

### 6.3. Retenciones de IVA (75%) e ISLR
* Cálculo automatizado de retenciones de IVA del 75% o 100% y retenciones de ISLR según la providencia fiscal vigente, generando el comprobante de retención correspondiente.

---

## 7. Tesorería y Finanzas

### 7.1. Cuentas por Cobrar (CxC)
* En **Tesorería > Cuentas por Cobrar**: Monitoreo de facturas emitidas a crédito.
* Registro de amortizaciones parciales o liquidación total con registro de referencia bancaria o medio de cobro.
* Reportes de antigüedad de saldos (por vencer, 1-15 días, 16-30 días, más de 30 días).

### 7.2. Cuentas por Pagar (CxP)
* En **Tesorería > Cuentas por Pagar**: Control de deudas con proveedores para programar pagos oportunamente y evitar morosidad.

### 7.3. Cuentas Bancarias y Conciliación
* Registro de cuentas bancarias en **Tesorería > Cuentas Bancarias** (Banesco, Mercantil, BDV, Provincial, Cuentas en Divisas).
* Conciliación bancaria comparando los movimientos registrados en el ERP con el estado de cuenta bancario.

---

## 8. Módulo Fiscal y Reportes SENIAT

### 8.1. Libros Oficiales de Compras y Ventas (Providencia 0049)
* Generación automática de los **Libros de Compras y Ventas** con formato oficial exigido por el SENIAT.
* Exportación a Excel y PDF con discriminación de base imponible, alícuotas (16%, 8%, 0%), IVA retenido, número de comprobante y número de control.

### 8.2. Impuesto a las Grandes Transacciones Financieras (IGTF 3%)
* Aplicación y desglose automático del IGTF del 3% en pagos recibidos en divisas extranjeras (USD en efectivo o transferencias en moneda extranjera).

---

## 9. Módulo Contable Auxiliar (VEN-NIF)

* Plan de cuentas flexible adaptado a la nomenclatura venezolana.
* Generación automática de asientos de diario originados por las ventas del POS, compras, ingresos y egresos de tesorería.
* Balance de comprobación y balance general auxiliar.

---

## 10. Nómina y Gestión de Talento Humano (LOTTT)

* Expedientes completos de trabajadores (cédula, cargo, salario base, fecha de ingreso).
* Cálculo de nómina quincenal y mensual bajo la Ley Orgánica del Trabajo (LOTTT).
* Deducciones legales automáticas: **IVSS (Seguro Social)**, **FAOV (Vivienda y Hábitat)**, **INCES**.
* Cálculo de horas extras diurnas y nocturnas, días feriados y bonificaciones.
* Generación de recibos de pago individuales en formato PDF.

---

## 11. Panel de Súper Administrador SaaS y Cotizador de Licencias

Herramienta de uso exclusivo para el Administrador Dueño del Sistema (**InfaGraSolution**), accesible desde el menú de usuario en **Panel SaaS** (`/admin`).

### 11.1. Control de Inquilinos y Licenciamiento
* Creación de nuevas empresas clientes con aislamiento de base de datos.
* Asignación de módulos activos y control de vencimiento de licencias (365 días).

### 11.2. Cotizador de Propuestas & Notas de Entrega en PDF
* Pestaña **"Cotizador & Propuestas (PDF)"**:
  - **Paquete Base Obligatorio:** Módulo Administrativo + Inventario & Almacén (WMS) a **$700 USD** el primer año (incluye setup cloud y 1 año de licencia) y **$400 USD** de renovación anual.
  - **Módulos Adicionales Separados:** Cada módulo a **$350 USD** el primer año y **$250 USD** de renovación anual (POS/Fiscal, Tesorería CxC/CxP, Compras, Contabilidad, Nómina).
  - **Descuentos y Acuerdos Especiales:** Switch para aplicar descuentos y campo amplio de observaciones para dejar asentados acuerdos de pago o promociones.
  - **Descarga Inmediata en PDF:**
    * 📄 **Propuesta Comercial & Contrato de Licencia (PDF):** Con membrete de InfaGraSolution, datos del cliente, tabla técnica, desglose financiero bimonetario, garantías y firmas.
    * 📦 **Nota de Entrega de Licencia (PDF):** Acta formal de entrega de software con número correlativo, módulos activos y firma de recibido conforme.
    * 🚀 **Aprovisionamiento Inmediato:** Botón para crear la empresa directamente con los módulos cotizados.

---

## 12. Preguntas Frecuentes (FAQ) y Soporte Técnico InfaGraSolution

### ¿Qué ocurre si se va el internet en el negocio?
El Punto de Venta (POS) cuenta con capacidad de contingencia operativa local para seguir emitiendo comprobantes de venta y tickets sin interrumpir el despacho. Al restablecerse la conexión, la información se sincroniza de forma segura con la base de datos en la nube.

### ¿Puedo cambiar la tasa del dólar manualmente si el BCV no ha actualizado?
Sí. El sistema permite ingresar a la configuración de inventario o facturación y ajustar la tasa cambiaria manual en caso de requerirse.

### ¿Mis datos están seguros frente a fallas del servidor?
Sí. InfaGraSolution realiza **copias de seguridad (backups) diarias y automatizadas** de cada base de datos PostgreSQL, garantizando la recuperación inmediata ante cualquier contingencia.

---

### 📞 Contacto Oficial de Soporte Técnico y Comercial

Para asistencia técnica, solicitudes de inducción, ampliación de módulos o soporte de emergencia:

* **Empresa:** InfaGraSolution
* **Director de Sistemas / Soporte:** Luis Infante
* **Teléfono / WhatsApp:** [0412-0161906](https://wa.me/584120161906)
* **Correo Electrónico:** [infagrasolution@gmail.com](mailto:infagrasolution@gmail.com)
* **Horario de Atención:** Lunes a Sábado de 8:00 AM a 6:00 PM (Soporte crítico POS 24/7)

---
*Manual oficial de usuario emitido por InfaGraSolution · Todos los derechos reservados.*
