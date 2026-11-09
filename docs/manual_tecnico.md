# 🛠️ Manual Técnico de Arquitectura y Operaciones — APEX ERP Enterprise
> **Versión 2.1 Enterprise Cloud** · InfaGraSolution · Sistema de Gestión Empresarial Multi-Tenant Adaptado a Venezuela  
> *Documentación técnica de arquitectura, base de datos, APIs, seguridad bancaria y despliegue para ingenieros y administradores de sistemas.*

---

## 📑 Tabla de Contenidos

1. [Arquitectura General y Principios de Diseño](#1-arquitectura-general-y-principios-de-diseño)
2. [Stack Tecnológico](#2-stack-tecnológico)
3. [Estrategia Multi-Tenant y Concurrencia](#3-estrategia-multi-tenant-y-concurrencia)
4. [Seguridad, Criptografía y Middleware RBAC](#4-seguridad-criptografía-y-middleware-rbac)
   - 4.1. Ciclo de Vida del JWT y `session_id`
   - 4.2. Matriz de Permisos RBAC Granulares
   - 4.3. Prevención de Escalada de Privilegios (`is_tenant_admin`)
   - 4.4. Mitigación de Ataques de Fuerza Bruta (Rate Limiting y Lockout)
   - 4.5. Control de Sesión Única y Concurrencia
   - 4.6. Cabeceras HTTP de Protección
   - 4.7. Sanitización Global de Excepciones y Trazabilidad
   - 4.8. Limitador de Tamaño de Payload (Anti-DoS)
5. [Modelo de Datos y Esquemas de Base de Datos](#5-modelo-de-datos-y-esquemas-de-base-de-datos)
6. [Catálogo de Servicios y API REST](#6-catálogo-de-servicios-y-api-rest)
7. [Variables de Entorno y Configuración](#7-variables-de-entorno-y-configuración)
8. [Procedimiento de Instalación y Despliegue](#8-procedimiento-de-instalación-y-despliegue)
9. [Migraciones de Base de Datos (Alembic)](#9-migraciones-de-base-de-datos-alembic)
10. [Mantenimiento, Respaldos y Monitoreo](#10-mantenimiento-respaldos-y-monitoreo)

---

## 1. Arquitectura General y Principios de Diseño

APEX ERP está diseñado bajo un modelo **desacoplado (Decoupled Client-Server Architecture)**, separando la lógica de presentación del motor de procesamiento transaccional y persistencia.

```mermaid
graph TD
    UserClient[Cliente Web / POS - React MUI] -- HTTPS / REST JSON --> NginxGateway[Nginx Reverse Proxy / SSL / Gzip]
    NginxGateway -- Port 8000 --> AppServer[Uvicorn / FastAPI Backend Asíncrono]
    
    subgraph Capa Backend
        AppServer --> SecurityLayer[Auth Middleware: JWT + Tenant Resolver + RBAC Guard]
        SecurityLayer --> RouterLayer[API Routers: Sales, Purchases, WMS, Treasury, Fiscal, Cash]
        RouterLayer --> ServiceLayer[Domain Services: Transacciones, Cálculos, Asientos Contables]
        ServiceLayer --> ORMLayer[SQLAlchemy 2.0 Async Session Engine]
    end

    subgraph Capa Persistencia PostgreSQL
        ORMLayer --> ConnPool[Async Connection Pool - asyncpg]
        ConnPool --> PublicSchema[(Schema 'public': Tenants, Users, Subscriptions)]
        ConnPool --> TenantSchema1[(Schema 'tenant_1': Empresa Alfa Operacional)]
        ConnPool --> TenantSchema2[(Schema 'tenant_2': Empresa Beta Operacional)]
    end
```

### Principios Fundamentales:
1. **Aislamiento Fuerte de Datos:** Garantía estricta de que ningún inquilino puede consultar ni alterar datos de otro inquilino, mediante esquemas lógicos PostgreSQL independientes (`SET search_path`).
2. **Concurrencia No Bloqueante:** Toda la capa de entrada/salida (I/O) en el backend está implementada mediante `asyncio` y el driver de alto desempeño `asyncpg`.
3. **Moneda Dual Transaccional:** Cada registro financiero conserva el monto en Dólares ($ USD), la tasa de cambio vigente al momento de la transacción (`exchange_rate`) y el equivalente en Bolívares (VES), garantizando auditoría histórica intacta ante devaluaciones.
4. **Idempotencia y Resiliencia:** Operaciones críticas como cierres de caja, anulaciones y emisiones fiscales manejan validaciones de estado y bloqueos para prevenir condiciones de carrera (*race conditions*).

---

## 2. Stack Tecnológico

### 2.1. Backend (Servicios y Lógica de Negocio)
* **Lenguaje:** Python 3.11+ / 3.12.
* **Framework Web:** FastAPI (ASGI de alto rendimiento).
* **Servidor de Aplicación:** Uvicorn con workers Gunicorn (`uvicorn.workers.UvicornWorker`).
* **ORM:** SQLAlchemy 2.0 (modo asíncrono con `AsyncSession`).
* **Driver PostgreSQL:** `asyncpg` (driver nativo C/Cython de máxima velocidad).
* **Validación y Serialización:** Pydantic v2 (`BaseModel`, `ConfigDict`).
* **Migraciones:** Alembic.
* **Criptografía:** `passlib` con `bcrypt`, `pyjwt` para tokens JWT.
* **Reportes:** `reportlab` para generación dinámica de PDFs vectoriales de alta fidelidad.

### 2.2. Frontend (Interfaz de Usuario)
* **Framework:** React 18 con TypeScript en modo estricto (`strict: true`).
* **Herramienta de Construcción:** Vite (compilación ultra rápida mediante Rollup y ESBuild).
* **Componentes Visuales:** Material-UI (MUI v6) con personalización de temas (Light/Dark mode) y soporte Responsive.
* **Manejo de Estado Global:** Zustand (tienda ligera para autenticación, branding y preferencias).
* **Sincronización y Caché:** `@tanstack/react-query` v5 (gestión de caché en segundo plano, mutaciones optimistas y reintentos automáticos).
* **Cliente HTTP:** Axios con interceptores automáticos de autenticación JWT y manejo centralizado de errores 401/403/500.

### 2.3. Base de Datos
* **Motor:** PostgreSQL 15+.
* **Pool de Conexiones:** SQLAlchemy QueuePool con capacidad de reciclaje de conexiones (`pool_recycle=1800`, `pool_pre_ping=True`).

---

## 3. Estrategia Multi-Tenant y Concurrencia

Nexus ERP emplea la estrategia **"Single Database, Separate Schemas"**:
* Existe una única base de datos física PostgreSQL.
* El esquema `public` almacena únicamente tablas maestras del ecosistema: `tenants`, `users` globales, `subscriptions` y configuraciones SaaS.
* Para cada empresa registrada se aprovisiona un esquema PostgreSQL dedicado con la nomenclatura `tenant_{tenant_id}` (ejemplo: `tenant_1`, `tenant_2`).

### 3.1. Resolución Dinámica de Esquema por Petición
1. El usuario envía una petición HTTP con el encabezado `Authorization: Bearer <JWT>`.
2. El middleware de autenticación decodifica el token y extrae el campo `tenant_id`.
3. Al adquirir la sesión asíncrona de base de datos (`AsyncSession`), se ejecuta de forma inmediata:
   ```sql
   SET search_path TO tenant_{tenant_id}, public;
   ```
4. A partir de esa instrucción, cualquier consulta SQL (`SELECT`, `INSERT`, `UPDATE`) busca automáticamente las tablas dentro del esquema del inquilino autenticado. Si un atacante intentase inyectar un ID foráneo, la consulta fallará o solo verá sus propios registros.

---

## 4. Seguridad, Criptografía y Middleware RBAC

### 4.1. Ciclo de Vida del JWT y `session_id`
* **Access Token:** Validez de 60 minutos. Contiene en su payload:
  * `sub`: ID único del usuario en el sistema.
  * `tenant_id`: ID del inquilino activo.
  * `session_id`: UUID criptográfico generado al iniciar sesión (`uuid4`). Permite invalidar sesiones de inmediato si el usuario inicia en otra máquina o si se revoca remotamente.
  * `is_superuser`: Bandera booleana de superadministrador global.
  * `roles`: Lista de roles asignados.
  * `exp`: Timestamp Unix de caducidad.
* **Refresh Token:** Validez de hasta 30 días para renovación transparente de sesión.
* **Criptografía:** Firmado con algoritmo HMAC-SHA256 (`HS256`) utilizando una clave `SECRET_KEY` de alta entropía (mínimo 32 caracteres). Si el entorno no define una clave robusta en modo producción, el sistema genera dinámicamente un token seguro de 64 caracteres hex y bloquea configuraciones vulnerables.

### 4.2. Matriz de Permisos RBAC Granulares
El acceso a cada controlador está blindado mediante las dependencias `require_permissions` y `require_module`:

| Dominio | Permisos Disponibles |
|---------|----------------------|
| **Ventas** | `sales:read`, `sales:write`, `sales:void`, `sales:delete` |
| **Inventario** | `inventory:read`, `inventory:write`, `inventory:transfer`, `inventory:adjust`, `inventory:charge`, `inventory:discharge`, `inventory:delete` |
| **Compras** | `purchases:read`, `purchases:write`, `purchases:approve` |
| **Tesorería / Caja** | `treasury:read`, `treasury:write`, `cash:open`, `cash:close`, `cash:audit` |
| **Contabilidad** | `accounting:read`, `accounting:write` |
| **Fiscal** | `fiscal:read`, `fiscal:write`, `fiscal:export` |
| **Nómina (LOTTT)** | `payroll:read`, `payroll:write` |
| **Usuarios & Roles** | `users:read`, `users:write` |
| **Sistema & Auditoría** | `settings:read`, `settings:write`, `audit:read` |

### 4.3. Prevención de Escalada de Privilegios (`is_tenant_admin`)
Para evitar que un usuario de empresa escale sus privilegios y modifique la licencia contratada, módulos habilitados o fecha de suscripción:
1. **Separación de Roles:** La columna `is_tenant_admin` en la tabla `public.users` distingue a los dueños de empresa de los empleados operativos y del superadministrador SaaS (`is_superuser`).
2. **Aislamiento de Perfil de Empresa (`TenantProfileUpdate`):** El endpoint `PUT /api/v1/tenants/me` solo permite actualizar información de identidad (nombre comercial, RIF, teléfono, dirección, logo y color primario). Cualquier intento de enviar `modules`, `subscription_end`, `is_active` o `parent_id` es ignorado o rechazado con error HTTP 403.
3. **Validación Estricta de Contraseñas:** Toda creación o modificación de clave exige una longitud mínima de 8 caracteres.

### 4.4. Mitigación de Ataques de Fuerza Bruta (Rate Limiting y Lockout)
1. **Control de Tasa por IP (`Rate Limiter`):** El endpoint `/api/v1/auth/login` restringe el tráfico a un máximo de 10 intentos por minuto por dirección IP de origen, respondiendo con HTTP 429 (`Too Many Requests`) si se supera el umbral.
2. **Bloqueo Preventivo Automático (`Fail2Ban` en memoria):** Al registrar 3 intentos consecutivos fallidos de contraseña:
   - La cuenta se bloquea (`is_locked = True`).
   - El sistema almacena la marca temporal del bloqueo.
   - Tras **15 minutos**, el bloqueo expira automáticamente, permitiendo reintentar sin necesidad de intervención técnica.
   - El Administrador de la empresa cuenta adicionalmente con el botón de **Desbloquear Cuenta** en el panel de usuarios para atención inmediata a sus empleados.

### 4.5. Control de Sesión Única y Concurrencia
* Cada inicio de sesión exitoso almacena en el registro del usuario (`active_session_id`) un identificador único de sesión.
* En cada petición protegida, el backend verifica que el `session_id` del token coincida con el `active_session_id` vigente en base de datos.
* Si el mismo usuario inicia sesión en otro equipo o navegador, la sesión anterior es revocada al instante (HTTP 401: *"Sesión invalidada. Se ha iniciado sesión desde otro dispositivo"*).

### 4.6. Cabeceras HTTP de Protección
El servidor inyecta en todas las respuestas cabeceras de seguridad de nivel bancario:
* `Strict-Transport-Security: max-age=31536000; includeSubDomains` (Obliga el uso de HTTPS estricto).
* `X-Frame-Options: DENY` (Protección contra Clickjacking).
* `X-Content-Type-Options: nosniff` (Inhabilita la autodetección de tipos MIME).
* `X-XSS-Protection: 1; mode=block` (Filtro nativo contra inyección de scripts).
* `Referrer-Policy: strict-origin-when-cross-origin` (Protección de metadatos de navegación).
* `Content-Security-Policy: default-src 'self' ...` (Aislamiento de scripts y recursos no autorizados).

### 4.7. Sanitización Global de Excepciones y Trazabilidad
* Cualquier excepción interna imprevista (error 500) es capturada por un middleware global.
* El traceback técnico detallado se registra en los logs del servidor junto a un código de rastreo aleatorio (`APEX-XXXXXXXX`).
* Al cliente web se le entrega únicamente una respuesta JSON sanitizada con el identificador de soporte, impidiendo la fuga de información sensible sobre la base de datos o rutas internas de archivos.

### 4.8. Limitador de Tamaño de Payload (Anti-DoS)
* Middleware de inspección de cabecera `Content-Length`.
* Rechaza peticiones que excedan los **15 Megabytes** con código HTTP 413 (`Payload Too Large`), previniendo saturación de memoria por subida masiva de datos maliciosos.

---

## 5. Modelo de Datos y Esquemas de Base de Datos

### 5.1. Tablas del Esquema `public`
* `tenants`: Información corporativa, RIF, subdominio, plan de suscripción, estado (`ACTIVE`, `SUSPENDED`).
* `users`: Credenciales de acceso, correo único, hash de contraseña en bcrypt, superuser flag.
* `user_tenants`: Relación muchos a muchos entre usuarios e inquilinos, asociando el `role_id` correspondiente.
* `subscriptions`: Registro de pagos y vigencia de licencias SaaS.

### 5.2. Tablas Principales de Esquema Inquilino (`tenant_{id}`)
* **Catálogo & WMS:**
  * `products`: SKU, nombre, descripción, costo base, margen, precio venta, unidad de medida, exento de IVA.
  * `warehouses`: Almacenes físicos y virtuales.
  * `product_warehouses`: Stock físico y disponible por almacén.
  * `batches`: Lotes con código, fecha de ingreso, fecha de vencimiento y existencias.
  * `inventory_movements`: Kardex general (`type`: `IN`, `OUT`, `TRANSFER`, `ADJUSTMENT`).
  * `dispatch_notes`: Guías de traslado entre almacenes.
* **Comercial:**
  * `customers`: Clientes con RIF/Cédula, dirección, crédito y teléfono.
  * `sales`: Cabecera de venta (número de factura, número de control, total USD, total VES, tasa BCV, estado `COMPLETED`, `ON_HOLD`, `VOIDED`).
  * `sale_items`: Líneas de factura con cantidad, precio unitario, descuento e IVA.
  * `quotations` & `quotation_items`: Presupuestos con fecha de caducidad.
  * `credit_notes` & `debit_notes`: Documentos tributarios rectificativos.
* **Proveedores & Compras:**
  * `suppliers`: Proveedores con RIF, razón social y datos fiscales.
  * `purchase_orders`: Órdenes de compra (`PENDING`, `APPROVED`, `RECEIVED`, `CANCELLED`).
  * `purchase_order_items`: Renglones de compra.
* **Caja & POS:**
  * `cash_sessions`: Turnos de caja (`OPEN`, `CLOSED`) con fondo inicial, hora de apertura, hora de cierre y usuario.
  * `cash_movements`: Transacciones individuales vinculadas a la sesión (`SALE`, `WITHDRAWAL`, `DEPOSIT`, `EXPENSE`).
* **Tesorería:**
  * `accounts_receivable`: Cuentas por cobrar con saldo pendiente y fecha de vencimiento.
  * `accounts_payable`: Cuentas por pagar a proveedores.
  * `treasury_payments`: Pagos y abonos recibidos o emitidos con referencia bancaria.
  * `bank_accounts`: Cuentas financieras registradas de la empresa.
* **Fiscal & Contabilidad:**
  * `fiscal_sales`: Registro homologado para Libro de Ventas SENIAT.
  * `fiscal_purchases`: Registro homologado para Libro de Compras SENIAT.
  * `chart_of_accounts`: Catálogo contable multinivel.
  * `journal_entries` & `journal_entry_lines`: Asientos de diario en partida doble.
* **Auditoría:**
  * `audit_logs`: Trazabilidad inmutable de operaciones del sistema.

---

## 6. Catálogo de Servicios y API REST

Todos los endpoints tienen como prefijo `/api/v1` y exigen encabezado `Authorization: Bearer <token>`.

### 6.1. Autenticación (`/api/v1/auth`)
* `POST /auth/login`: Autentica credenciales y devuelve tokens JWT (`access_token`, `refresh_token`) e información de usuario.
* `POST /auth/refresh`: Renueva el `access_token` a partir de un `refresh_token` válido.
* `GET /auth/me`: Retorna el perfil del usuario autenticado, roles y permisos en el tenant activo.
* `POST /auth/logout`: Revoca la sesión en el cliente.

### 6.2. Dashboard & KPIs (`/api/v1/dashboard`)
* `GET /dashboard/kpis`: Retorna métricas consolidadas: ventas del mes, cobranzas, cuentas por cobrar, cuentas por pagar, valor de inventario y alertas de stock crítico.
* `GET /dashboard/sales-trend`: Historial temporal de ventas y costos (últimos 7, 30 o 90 días).
* `GET /dashboard/top-products`: Ranking de productos de mayor rotación y rentabilidad.
* `GET /dashboard/cash-flow`: Proyección de flujo de caja para los próximos 30 días.

### 6.3. Ventas & Facturación (`/api/v1/sales`)
* `GET /sales`: Lista facturas con filtros de fecha, cliente y estado (`COMPLETED`, `ON_HOLD`, `VOIDED`).
* `POST /sales`: Registra una nueva venta, descuenta inventario, actualiza caja o CxC y genera correlativo fiscal.
* `GET /sales/{id}`: Obtiene el detalle de una factura.
* `POST /sales/{id}/complete`: Completa una venta en espera (`ON_HOLD`) deduciendo el stock de almacén de forma definitiva.
* `GET /sales/{id}/invoice`: Genera el comprobante de factura fiscal en PDF (formato Carta).
* `GET /sales/{id}/ticket`: Genera el Ticket Térmico de Venta para impresoras POS de 80mm o 58mm.
* `POST /sales/credit-notes`: Emite una Nota de Crédito SENIAT con reposición de existencias al almacén y ajuste en CxC.
* `GET /sales/customers`: Catálogo de clientes con paginación y búsqueda por RIF/nombre.
* `POST /sales/customers`: Crea un nuevo cliente.

### 6.4. Punto de Venta & Caja (`/api/v1/cash`) y Contingencia Offline
* **Arquitectura Offline-First:** El módulo POS implementa una cola local en cliente (`offlineQueue.ts`) que captura y almacena ventas locales ante interrupciones de internet o fallas de suministro eléctrico, con auto-sincronización en segundo plano al restablecerse la conectividad.
* `POST /cash/open`: Abre una sesión de caja indicando el fondo inicial en USD y Bolívares.
* `POST /cash/close`: Cierra la sesión activa con conteo ciego, desglose multimoneda y cálculo de faltante/sobrante.
* `GET /cash/current`: Consulta el estado actual de la sesión de caja del usuario en turno.
* `POST /cash/movements`: Registra un retiro de efectivo o gasto menor de caja.
* `GET /cash/sessions`: Historial de cierres de caja con filtros de fecha y cajero.
* `GET /cash/sessions/{id}/report`: Genera el reporte de corte de caja / Cierre Z detallado.

### 6.5. Inventario & WMS (`/api/v1/inventory`)
* `GET /inventory/products`: Lista de productos con stock total, costo, precio e indicador de stock mínimo.
* `POST /inventory/products`: Crea un nuevo producto con SKU único.
* `PUT /inventory/products/{id}`: Actualiza datos del producto o precios.
* `POST /inventory/movements/in`: Registra un cargo de inventario manual.
* `POST /inventory/movements/out`: Registra un descargo de inventario con justificación.
* `POST /inventory/transfers`: Realiza una transferencia de mercancía entre almacenes.
* `POST /inventory/audits`: Inicia una auditoría de conteo físico.
* `POST /inventory/audits/{id}/apply`: Aplica los ajustes de existencias derivados de una auditoría.
* `GET /inventory/exchange-rate/current`: Obtiene la tasa de cambio vigente del BCV.
* `POST /inventory/exchange-rate`: Actualiza manualmente la tasa de cambio y recalcula precios en Bolívares.

### 6.6. Compras (`/api/v1/purchases`)
* `GET /purchases/orders`: Lista órdenes de compra por estado.
* `POST /purchases/orders`: Crea una nueva orden de compra para un proveedor.
* `POST /purchases/orders/{id}/approve`: Aprueba la orden para compra.
* `POST /purchases/orders/{id}/receive`: Procesa la recepción física de mercancía en almacén, incrementa stock y genera Cuenta por Pagar neta (descontando retenciones de ley).
* `GET /purchases/suppliers`: Directorio de proveedores.
* `POST /purchases/suppliers`: Registra un proveedor.

### 6.7. Tesorería (`/api/v1/treasury`)
* `GET /treasury/accounts-receivable`: Cuentas por cobrar con balance pendiente y estatus de morosidad.
* `POST /treasury/accounts-receivable/{id}/payments`: Registra un cobro a cliente con comprobante.
* `GET /treasury/accounts-payable`: Cuentas por pagar a proveedores (monto neto tras retenciones SENIAT).
* `POST /treasury/accounts-payable/{id}/payments`: Registra un egreso/pago a proveedor.
* `GET /treasury/bank-accounts`: Gestión de cuentas bancarias y arqueo consolidado multimoneda.
* `GET /treasury/aging-report`: Reporte de antigüedad de saldos en tramos de 30, 60, 90 y +90 días.
* `POST /treasury/bank-reconciliation`: Concilia movimientos bancarios frente a cobros registrados.

### 6.8. Módulo Fiscal SENIAT (`/api/v1/fiscal`)
* `GET /fiscal/libro-ventas`: Consulta el Libro de Ventas en formato oficial SENIAT para un mes y año específicos (filtrado directo en SQL).
* `GET /fiscal/libro-ventas/export`: Exporta el Libro de Ventas en formato Excel (.xlsx).
* `GET /fiscal/libro-compras`: Consulta el Libro de Compras SENIAT por período.
* `GET /fiscal/libro-compras/export`: Exporta el Libro de Compras en formato Excel.
* `GET /fiscal/comprobante-iva/{id}`: Genera el Comprobante Oficial de Retención de IVA en PDF (Providencia SNAT/2015/0049).
* `GET /fiscal/txt-retenciones-iva`: Genera el archivo TXT para declaración masiva de retenciones en el portal SENIAT.

### 6.9. Nómina y Gestión Humana LOTTT (`/api/v1/payroll`)
* `GET /payroll/employees`: Listado de trabajadores activos e inactivos.
* `POST /payroll/employees`: Registra nuevo trabajador con datos de leyes (SSO, RPE, FAOV, Cestaticket).
* `GET /payroll/periods`: Lista períodos de nómina con sus totales consolidados.
* `POST /payroll/periods`: Abre nuevo período quincenal o semanal de nómina.
* `POST /payroll/periods/{id}/calculate`: Ejecuta el cálculo automático de haberes y deducciones de ley.
* `POST /payroll/periods/{id}/close`: Cierra la nómina y genera el asiento contable automático en el Libro Diario.
* `GET /payroll/receipts/{id}/pdf`: Genera el recibo individual de pago de nómina LOTTT en PDF.

### 6.10. Contabilidad General VEN-NIF (`/api/v1/accounting`)
* `GET /accounting/accounts`: Plan de cuentas jerárquico VEN-NIF.
* `POST /accounting/accounts`: Agrega una cuenta contable al catálogo.
* `POST /accounting/accounts/import`: Importación masiva de plan de cuentas vía CSV.
* `GET /accounting/journal-entries`: Comprobantes de diario con detalle de débitos y créditos en partida doble.
* `POST /accounting/journal-entries`: Registra un asiento de diario manual cuadrado.
* `GET /accounting/trial-balance`: Balance de comprobación de sumas y saldos con 4 columnas y verificación de cuadre.
* `GET /accounting/balance-sheet`: Estado de Situación Financiera (Activo = Pasivo + Capital + Resultados).
* `POST /accounting/year-end-closing`: Asiento de cierre de cuentas nominales de ejercicio fiscal.

---

## 7. Variables de Entorno y Configuración

### 7.1. Backend (`Backend/.env`)
```ini
# Configuración del Entorno
ENVIRONMENT=production
DEBUG=false
PROJECT_NAME="Nexus ERP Enterprise"

# Base de Datos PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:TuPasswordSeguro@localhost:5432/nexus_erp_db
DATABASE_SYNC_URL=postgresql://postgres:TuPasswordSeguro@localhost:5432/nexus_erp_db

# Seguridad Criptográfica
SECRET_KEY=c3f1b49e8a7d2e0f1a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=14

# CORS (Orígenes Permitidos)
CORS_ORIGINS=["https://erp.tuempresa.com", "http://localhost:5173"]

# Configuración BCV y Fiscal
BCV_API_URL=https://pydolarvenezuela-api.vercel.app/api/v1/dollar
DEFAULT_TAX_RATE=0.16
```

### 7.2. Frontend (`frontend/.env`)
```ini
VITE_API_BASE_URL=https://api.tuempresa.com/api/v1
VITE_APP_TITLE="Nexus ERP Enterprise"
VITE_DEFAULT_CURRENCY=USD
VITE_SECONDARY_CURRENCY=VES
```

---

## 8. Procedimiento de Instalación y Despliegue

### 8.1. Despliegue en Servidor Linux (Ubuntu 22.04 LTS / Debian 12)

#### 1. Requisitos Previos:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx git
```

#### 2. Configuración de PostgreSQL:
```bash
sudo -u postgres psql
CREATE DATABASE nexus_erp_db;
CREATE USER nexus_user WITH ENCRYPTED PASSWORD 'ClaveSegura123!';
GRANT ALL PRIVILEGES ON DATABASE nexus_erp_db TO nexus_user;
\q
```

#### 3. Instalación del Backend:
```bash
cd /var/www/nexus-erp/Backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
alembic upgrade head
```

#### 4. Servicio Systemd para el Backend (`/etc/systemd/system/nexus-backend.service`):
```ini
[Unit]
Description=Nexus ERP FastAPI Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nexus-erp/Backend
Environment="PATH=/var/www/nexus-erp/Backend/venv/bin"
ExecStart=/var/www/nexus-erp/Backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start nexus-backend
sudo systemctl enable nexus-backend
```

#### 5. Compilación del Frontend:
```bash
cd /var/www/nexus-erp/frontend
npm install
npm run build
# Los archivos estáticos optimizados se generarán en /var/www/nexus-erp/frontend/dist
```

#### 6. Configuración de Nginx (`/etc/nginx/sites-available/nexus-erp`):
```nginx
server {
    listen 80;
    server_name erp.tuempresa.com;

    # Redirección forzada a HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name erp.tuempresa.com;

    ssl_certificate /etc/letsencrypt/live/erp.tuempresa.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/erp.tuempresa.com/privkey.pem;

    # Cabeceras de Seguridad
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Frontend SPA
    location / {
        root /var/www/nexus-erp/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/nexus-erp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 9. Migraciones de Base de Datos (Alembic)

Cuando se introducen nuevos campos o entidades en el backend:
1. Generar la revisión de migración automática:
   ```bash
   alembic revision --autogenerate -m "descripcion_del_cambio"
   ```
2. Inspeccionar el script generado en `Backend/alembic/versions/` para validar compatibilidad multi-tenant.
3. Aplicar los cambios sobre la base de datos:
   ```bash
   alembic upgrade head
   ```

---

## 10. Mantenimiento, Respaldos y Monitoreo

### 10.1. Utilidad de Respaldo Automatizado Multi-Tenant (`scripts/backup_db.py`)
El sistema incluye un script asíncrono en Python especializado en respaldos completos o por empresa para entornos PostgreSQL tradicionales o Serverless (Neon DB):

```bash
# Respaldo completo de todas las tablas públicas y todos los esquemas de empresas:
python scripts/backup_db.py --all

# Respaldo específico de una sola empresa (ejemplo: Empresa ID 2):
python scripts/backup_db.py --tenant 2
```

**Características del Respaldo:**
* Genera archivos comprimidos `.json.gz` en el directorio `Backend/backups/`.
* Extrae la estructura de tablas y todos los registros con serialización de tipos nativos (fechas, UUIDs, decimales y booleanos).
* Nomenclatura automática con timestamp: `apex_backup_full_YYYYMMDD_HHMMSS.json.gz`.
* El directorio `backups/` está explícitamente excluido del control de versiones (`.gitignore`) para evitar filtración accidental de información comercial.

### 10.2. Respaldo Nativo de PostgreSQL (`pg_dump`)
Para respaldos binarios o de volcado SQL completo a nivel de sistema operativo:
```bash
0 2 * * * pg_dump "$DATABASE_URL" | gzip > /var/backups/apex/apex_db_$(date +\%Y\%m\%d_\%H\%M).sql.gz
```

### 10.3. Restauración de Emergencia
```bash
# Restauración a partir de volcado SQL comprimido:
gunzip -c /var/backups/apex/apex_db_20261108_0200.sql.gz | psql "$DATABASE_URL"
```

### 10.4. Monitoreo de Procesos y Logs de Auditoría
* **Logs del Backend en tiempo real:**
  ```bash
  sudo journalctl -u apex-backend -f
  ```
* **Logs de acceso y errores de Nginx:**
  ```bash
  tail -f /var/log/nginx/access.log
  tail -f /var/log/nginx/error.log
  ```
* **Punto de Estado del Servicio (Healthcheck):**
  - Endpoint: `GET /health`
  - Respuesta: `{"status": "ok", "app": "APEX ERP", "version": "2.1.0"}`

---
*Manual Técnico de Arquitectura y Operaciones — APEX ERP Enterprise Cloud © 2026 InfaGraSolution.*
