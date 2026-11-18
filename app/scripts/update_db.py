import asyncio
import os
from sqlalchemy import select, text
from app.core.database import MasterSessionLocal, master_engine, Base, get_tenant_engine
from app.domain.tenant import Tenant

# Importar todos los modelos para que Base.metadata contenga todas las tablas
import app.domain

TENANT_SCHEMA_MIGRATIONS = """
-- 1. Products: Nuevos campos y conversión a NUMERIC
ALTER TABLE products ADD COLUMN IF NOT EXISTS barcode VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS price_2 NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE products ADD COLUMN IF NOT EXISTS price_3 NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE products ADD COLUMN IF NOT EXISTS tax_exempt BOOLEAN DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(18, 4) DEFAULT 16.0000;
ALTER TABLE products ADD COLUMN IF NOT EXISTS margin_percent NUMERIC(18, 4) DEFAULT 30.0000;
DO $$ BEGIN
    ALTER TABLE products ALTER COLUMN price TYPE NUMERIC(18, 4) USING price::numeric(18, 4);
    ALTER TABLE products ALTER COLUMN price_2 TYPE NUMERIC(18, 4) USING price_2::numeric(18, 4);
    ALTER TABLE products ALTER COLUMN price_3 TYPE NUMERIC(18, 4) USING price_3::numeric(18, 4);
    ALTER TABLE products ALTER COLUMN cost TYPE NUMERIC(18, 4) USING cost::numeric(18, 4);
    ALTER TABLE products ALTER COLUMN average_cost TYPE NUMERIC(18, 4) USING average_cost::numeric(18, 4);
    ALTER TABLE products ALTER COLUMN min_stock TYPE NUMERIC(18, 4) USING min_stock::numeric(18, 4);
    ALTER TABLE products ALTER COLUMN max_stock TYPE NUMERIC(18, 4) USING max_stock::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 2. Sales: Almacén, control fiscal SENIAT, IGTF, descuentos
ALTER TABLE sales ADD COLUMN IF NOT EXISTS warehouse_id INTEGER DEFAULT 1;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS control_number VARCHAR(50);
ALTER TABLE sales ADD COLUMN IF NOT EXISTS igtf_amount NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS discount_total NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS voided_reason TEXT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS notes TEXT;
DO $$ BEGIN
    ALTER TABLE sales ALTER COLUMN subtotal TYPE NUMERIC(18, 4) USING subtotal::numeric(18, 4);
    ALTER TABLE sales ALTER COLUMN tax_total TYPE NUMERIC(18, 4) USING tax_total::numeric(18, 4);
    ALTER TABLE sales ALTER COLUMN total TYPE NUMERIC(18, 4) USING total::numeric(18, 4);
    ALTER TABLE sales ALTER COLUMN exchange_rate TYPE NUMERIC(18, 4) USING exchange_rate::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 3. Sale Details: Descuentos y precisión
ALTER TABLE sale_details ADD COLUMN IF NOT EXISTS discount_percent NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE sale_details ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(18, 4) DEFAULT 0.0000;
DO $$ BEGIN
    ALTER TABLE sale_details ALTER COLUMN quantity TYPE NUMERIC(18, 4) USING quantity::numeric(18, 4);
    ALTER TABLE sale_details ALTER COLUMN unit_price TYPE NUMERIC(18, 4) USING unit_price::numeric(18, 4);
    ALTER TABLE sale_details ALTER COLUMN subtotal TYPE NUMERIC(18, 4) USING subtotal::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 4. Customers: Crédito comercial
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_days INTEGER DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS contact_person VARCHAR(150);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS notes TEXT;

-- 5. Purchases: Almacén, factura, control proveedor y retenciones
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS warehouse_id INTEGER DEFAULT 1;
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(100);
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS control_number VARCHAR(100);
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS iva_withholding NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS islr_withholding NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE purchases ADD COLUMN IF NOT EXISTS notes TEXT;
DO $$ BEGIN
    ALTER TABLE purchases ALTER COLUMN subtotal TYPE NUMERIC(18, 4) USING subtotal::numeric(18, 4);
    ALTER TABLE purchases ALTER COLUMN tax_total TYPE NUMERIC(18, 4) USING tax_total::numeric(18, 4);
    ALTER TABLE purchases ALTER COLUMN total TYPE NUMERIC(18, 4) USING total::numeric(18, 4);
    ALTER TABLE purchases ALTER COLUMN exchange_rate TYPE NUMERIC(18, 4) USING exchange_rate::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 6. Purchase Details: Recepción parcial
ALTER TABLE purchase_details ADD COLUMN IF NOT EXISTS received_quantity NUMERIC(18, 4) DEFAULT 0.0000;
DO $$ BEGIN
    ALTER TABLE purchase_details ALTER COLUMN quantity TYPE NUMERIC(18, 4) USING quantity::numeric(18, 4);
    ALTER TABLE purchase_details ALTER COLUMN cost_price TYPE NUMERIC(18, 4) USING cost_price::numeric(18, 4);
    ALTER TABLE purchase_details ALTER COLUMN subtotal TYPE NUMERIC(18, 4) USING subtotal::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 7. Suppliers: Retenciones y datos bancarios
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS contact_person VARCHAR(150);
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS bank_name VARCHAR(100);
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS bank_account VARCHAR(50);
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS payment_terms VARCHAR(100);
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS credit_days INTEGER DEFAULT 0;
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS is_withholding_agent BOOLEAN DEFAULT FALSE;
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS notes TEXT;

-- 8. Treasury: Cuentas bancarias y multimoneda
ALTER TABLE accounts_receivable ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE accounts_receivable ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE accounts_receivable ADD COLUMN IF NOT EXISTS exchange_rate NUMERIC(18, 4) DEFAULT 1.0000;
DO $$ BEGIN
    ALTER TABLE accounts_receivable ALTER COLUMN total_amount TYPE NUMERIC(18, 4) USING total_amount::numeric(18, 4);
    ALTER TABLE accounts_receivable ALTER COLUMN remaining_amount TYPE NUMERIC(18, 4) USING remaining_amount::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

ALTER TABLE accounts_payable ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE accounts_payable ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE accounts_payable ADD COLUMN IF NOT EXISTS exchange_rate NUMERIC(18, 4) DEFAULT 1.0000;
DO $$ BEGIN
    ALTER TABLE accounts_payable ALTER COLUMN total_amount TYPE NUMERIC(18, 4) USING total_amount::numeric(18, 4);
    ALTER TABLE accounts_payable ALTER COLUMN remaining_amount TYPE NUMERIC(18, 4) USING remaining_amount::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

ALTER TABLE treasury_payments ADD COLUMN IF NOT EXISTS bank_account_id INTEGER;
ALTER TABLE treasury_payments ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE treasury_payments ADD COLUMN IF NOT EXISTS exchange_rate NUMERIC(18, 4) DEFAULT 1.0000;
ALTER TABLE treasury_payments ADD COLUMN IF NOT EXISTS notes TEXT;
DO $$ BEGIN
    ALTER TABLE treasury_payments ALTER COLUMN amount TYPE NUMERIC(18, 4) USING amount::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 9. Cash Sessions: Arqueo bimonetario USD / VES
ALTER TABLE cash_sessions ADD COLUMN IF NOT EXISTS difference NUMERIC(18, 4);
ALTER TABLE cash_sessions ADD COLUMN IF NOT EXISTS starting_cash_ves NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE cash_sessions ADD COLUMN IF NOT EXISTS expected_cash_ves NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE cash_sessions ADD COLUMN IF NOT EXISTS actual_cash_ves NUMERIC(18, 4);
ALTER TABLE cash_sessions ADD COLUMN IF NOT EXISTS difference_ves NUMERIC(18, 4);
ALTER TABLE cash_sessions ADD COLUMN IF NOT EXISTS notes TEXT;
DO $$ BEGIN
    ALTER TABLE cash_sessions ALTER COLUMN starting_cash TYPE NUMERIC(18, 4) USING starting_cash::numeric(18, 4);
    ALTER TABLE cash_sessions ALTER COLUMN expected_cash TYPE NUMERIC(18, 4) USING expected_cash::numeric(18, 4);
    ALTER TABLE cash_sessions ALTER COLUMN actual_cash TYPE NUMERIC(18, 4) USING actual_cash::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 10. Accounting: Precisión y estado
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'POSTED';
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD';
ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS exchange_rate NUMERIC(18, 4) DEFAULT 1.0000;
ALTER TABLE debit_notes ADD COLUMN IF NOT EXISTS control_number VARCHAR(50);
DO $$ BEGIN
    ALTER TABLE accounts ALTER COLUMN balance TYPE NUMERIC(18, 4) USING balance::numeric(18, 4);
    ALTER TABLE journal_entry_details ALTER COLUMN debit TYPE NUMERIC(18, 4) USING debit::numeric(18, 4);
    ALTER TABLE journal_entry_details ALTER COLUMN credit TYPE NUMERIC(18, 4) USING credit::numeric(18, 4);
    ALTER TABLE debit_notes ALTER COLUMN amount TYPE NUMERIC(18, 4) USING amount::numeric(18, 4);
    ALTER TABLE bank_statement_lines ALTER COLUMN amount TYPE NUMERIC(18, 4) USING amount::numeric(18, 4);
EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 11. Payroll: Tablas de Nómina LOTTT
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    national_id VARCHAR(50) NOT NULL,
    rif VARCHAR(50),
    email VARCHAR(150),
    phone VARCHAR(50),
    address TEXT,
    job_title VARCHAR(150) NOT NULL,
    department VARCHAR(100) DEFAULT 'General',
    hire_date DATE NOT NULL,
    termination_date DATE,
    salary_usd NUMERIC(18, 4) DEFAULT 0.0000,
    salary_ves NUMERIC(18, 4) DEFAULT 0.0000,
    currency VARCHAR(10) DEFAULT 'USD',
    payment_frequency VARCHAR(20) DEFAULT 'BIWEEKLY',
    cestaticket_usd NUMERIC(18, 4) DEFAULT 40.0000,
    bank_name VARCHAR(100),
    bank_account VARCHAR(50),
    applies_sso BOOLEAN DEFAULT TRUE,
    applies_rpe BOOLEAN DEFAULT TRUE,
    applies_faov BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by_id INTEGER,
    created_by_name VARCHAR,
    updated_by_id INTEGER,
    updated_by_name VARCHAR
);

CREATE TABLE IF NOT EXISTS payroll_periods (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(150) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    period_type VARCHAR(20) DEFAULT 'BIWEEKLY',
    exchange_rate NUMERIC(18, 4) DEFAULT 1.0000,
    status VARCHAR(20) DEFAULT 'DRAFT',
    total_salaries_ves NUMERIC(18, 4) DEFAULT 0.0000,
    total_cestaticket_ves NUMERIC(18, 4) DEFAULT 0.0000,
    total_deductions_ves NUMERIC(18, 4) DEFAULT 0.0000,
    total_net_ves NUMERIC(18, 4) DEFAULT 0.0000,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by_id INTEGER,
    created_by_name VARCHAR,
    updated_by_id INTEGER,
    updated_by_name VARCHAR
);

CREATE TABLE IF NOT EXISTS payroll_receipts (
    id SERIAL PRIMARY KEY,
    payroll_period_id INTEGER NOT NULL REFERENCES payroll_periods(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    receipt_number VARCHAR(50) NOT NULL,
    base_salary_ves NUMERIC(18, 4) DEFAULT 0.0000,
    cestaticket_ves NUMERIC(18, 4) DEFAULT 0.0000,
    other_bonuses_ves NUMERIC(18, 4) DEFAULT 0.0000,
    total_earnings_ves NUMERIC(18, 4) DEFAULT 0.0000,
    sso_deduction_ves NUMERIC(18, 4) DEFAULT 0.0000,
    rpe_deduction_ves NUMERIC(18, 4) DEFAULT 0.0000,
    faov_deduction_ves NUMERIC(18, 4) DEFAULT 0.0000,
    other_deductions_ves NUMERIC(18, 4) DEFAULT 0.0000,
    total_deductions_ves NUMERIC(18, 4) DEFAULT 0.0000,
    net_amount_ves NUMERIC(18, 4) DEFAULT 0.0000,
    net_amount_usd NUMERIC(18, 4) DEFAULT 0.0000,
    exchange_rate NUMERIC(18, 4) DEFAULT 1.0000,
    status VARCHAR(20) DEFAULT 'CALCULATED',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by_id INTEGER,
    created_by_name VARCHAR,
    updated_by_id INTEGER,
    updated_by_name VARCHAR
);

-- 12. System Movements & Stock Summary: Campos forenses y stock mínimo por almacén
ALTER TABLE system_movements ADD COLUMN IF NOT EXISTS ip_address VARCHAR(64);
ALTER TABLE system_movements ADD COLUMN IF NOT EXISTS user_agent VARCHAR(300);
ALTER TABLE system_movements ADD COLUMN IF NOT EXISTS endpoint VARCHAR(200);
ALTER TABLE stock_summary ADD COLUMN IF NOT EXISTS min_stock NUMERIC(18, 4) DEFAULT 0.0000;

-- 13. Payroll ORM alignment (employees, payroll_periods, payroll_receipts)
ALTER TABLE employees ADD COLUMN IF NOT EXISTS tenant_id INTEGER;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS tax_id VARCHAR(30);
ALTER TABLE employees ADD COLUMN IF NOT EXISTS position VARCHAR(100) DEFAULT 'Personal Operativo';
ALTER TABLE employees ADD COLUMN IF NOT EXISTS base_salary_usd NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS base_salary_ves NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS sso_eligible BOOLEAN DEFAULT TRUE;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS rpe_eligible BOOLEAN DEFAULT TRUE;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS faov_eligible BOOLEAN DEFAULT TRUE;
ALTER TABLE employees ADD COLUMN IF NOT EXISTS cestaticket_eligible BOOLEAN DEFAULT TRUE;
DO $$ BEGIN
    ALTER TABLE employees ALTER COLUMN job_title DROP NOT NULL;
    ALTER TABLE employees ALTER COLUMN job_title SET DEFAULT '';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

ALTER TABLE payroll_periods ADD COLUMN IF NOT EXISTS tenant_id INTEGER;
ALTER TABLE payroll_periods ADD COLUMN IF NOT EXISTS payment_date DATE DEFAULT CURRENT_DATE;
ALTER TABLE payroll_periods ADD COLUMN IF NOT EXISTS total_gross NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_periods ADD COLUMN IF NOT EXISTS total_deductions NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_periods ADD COLUMN IF NOT EXISTS total_net NUMERIC(18, 4) DEFAULT 0.0000;
DO $$ BEGIN
    ALTER TABLE payroll_periods ALTER COLUMN code DROP NOT NULL;
    ALTER TABLE payroll_periods ALTER COLUMN code SET DEFAULT '';
EXCEPTION WHEN OTHERS THEN NULL; END $$;

ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS tenant_id INTEGER;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS period_id INTEGER;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS base_salary_amount NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS cesta_ticket NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS bonuses NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS overtime NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS gross_total NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS sso_deduction NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS rpe_deduction NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS faov_deduction NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS other_deductions NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS total_deductions NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS net_payable NUMERIC(18, 4) DEFAULT 0.0000;
ALTER TABLE payroll_receipts ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USD';
DO $$ BEGIN
    ALTER TABLE payroll_receipts ALTER COLUMN payroll_period_id DROP NOT NULL;
    ALTER TABLE payroll_receipts ALTER COLUMN receipt_number DROP NOT NULL;
    ALTER TABLE payroll_receipts ALTER COLUMN receipt_number SET DEFAULT '';
EXCEPTION WHEN OTHERS THEN NULL; END $$;
"""


def _split_sql_statements(sql_script: str) -> list[str]:
    """Divide un script SQL en sentencias individuales respetando bloques DO $$ ... END $$;."""
    statements: list[str] = []
    current: list[str] = []
    in_dollar_block = False

    for raw_line in sql_script.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        current.append(raw_line)
        if "$$" in line:
            # Alterna estado si aparece un delimitador $$ (y si hay dos en la misma línea vuelve al mismo estado)
            if line.count("$$") % 2 == 1:
                in_dollar_block = not in_dollar_block
        if not in_dollar_block and line.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)
    return statements


async def ensure_tenant_schema(tenant_id: int) -> None:
    """Garantiza que el esquema, tablas y columnas de un tenant estén 100% actualizados."""
    schema_name = f"tenant_{tenant_id}"
    async with master_engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

    engine = get_tenant_engine(tenant_id)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ejecutar cada sentencia individualmente (asyncpg no permite múltiples comandos en un prepared statement)
    for stmt in _split_sql_statements(TENANT_SCHEMA_MIGRATIONS):
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as mig_err:
            print(f"Migration notice for Tenant {tenant_id}: {mig_err}")

async def update_all_databases():
    print("Updating Master Database...")
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Running automatic database branding migration...")
    try:
        async with master_engine.begin() as conn:
            await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_tenant_admin BOOLEAN DEFAULT FALSE"))
            await conn.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS custom_database_url VARCHAR(500)"))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS security_audit_logs (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                    tenant_id INTEGER,
                    user_id INTEGER,
                    username VARCHAR(150),
                    ip_address VARCHAR(64),
                    user_agent VARCHAR(350),
                    module VARCHAR(80) NOT NULL,
                    action VARCHAR(120) NOT NULL,
                    http_method VARCHAR(16) NOT NULL,
                    endpoint_path VARCHAR(255) NOT NULL,
                    status_code INTEGER,
                    payload_summary TEXT
                )
            """))
            # Backfill: el primer usuario de cada tenant (o 'demo') se marca como is_tenant_admin
            await conn.execute(text("""
                UPDATE users SET is_tenant_admin = TRUE 
                WHERE username = 'demo' 
                   OR (is_superuser = FALSE AND id IN (
                       SELECT MIN(id) FROM users WHERE is_superuser = FALSE GROUP BY tenant_id
                   ))
            """))

        async with MasterSessionLocal() as session:
            await session.execute(text("UPDATE tenants SET name = 'APEX MASTER CORP' WHERE id = 1"))
            await session.execute(text("UPDATE tenants SET email = 'infagrasolution@gmail.com' WHERE id = 1"))
            await session.execute(text("UPDATE tenants SET name = 'DEMO - APEX ERP' WHERE name = 'DEMO - NEXUS ERP'"))
            await session.execute(text("UPDATE tenants SET email = 'demo@apexerp.com' WHERE email = 'demo@nexuserp.com'"))
            await session.execute(text("""
                UPDATE users SET username = 'linfante'
                WHERE username = 'admin' AND is_superuser = TRUE
                  AND NOT EXISTS (SELECT 1 FROM users WHERE username = 'linfante')
            """))
            await session.execute(text("""
                UPDATE users SET is_superuser = TRUE, is_active = TRUE, tenant_id = 1
                WHERE username = 'linfante'
            """))
            await session.execute(text("UPDATE users SET email = 'infagrasolution@gmail.com' WHERE username IN ('admin', 'linfante')"))
            await session.execute(text("UPDATE users SET email = 'demo@apexerp.com' WHERE email = 'demo@nexuserp.com'"))
            await session.execute(text("UPDATE tenants SET subscription_end = '2027-05-28 23:59:59' WHERE LOWER(name) LIKE '%kprishop%'"))
            await session.commit()
            print("Successfully verified tenant and user records.")
    except Exception as db_err:
        print(f"Branding update notice: {db_err}")
    
    print("Updating Tenant Databases (PostgreSQL)...")
    try:
        async with MasterSessionLocal() as session:
            stmt = select(Tenant)
            result = await session.execute(stmt)
            tenants = result.scalars().all()
            
            for tenant in tenants:
                print(f"Ensuring schema, tables and columns for Tenant {tenant.id} ({tenant.name})...")
                await ensure_tenant_schema(tenant.id)

                # Si es la empresa DEMO, asegurar logo corporativo SVG y datos de inducción precargados
                if "demo" in (tenant.name or "").lower():
                    try:
                        from app.core.database import get_tenant_session_context
                        from app.services.demo_seed_service import DemoSeedService, DEMO_COMPANY_LOGO_DATA_URI
                        if not getattr(tenant, "logo_url", None) or str(tenant.logo_url).startswith("/uploads"):
                            tenant.logo_url = DEMO_COMPANY_LOGO_DATA_URI
                            await session.commit()
                        async with get_tenant_session_context(tenant.id) as t_session:
                            await DemoSeedService.seed_demo_company_data(t_session, session, tenant.id)
                            print(f"Demo data seeded/verified for Tenant {tenant.id} ({tenant.name}).")
                    except Exception as seed_err:
                        print(f"Demo seed notice for Tenant {tenant.id}: {seed_err}")
                        
        print("PostgreSQL tenant databases and schemas updated successfully!")
    except Exception as e:
        print(f"PostgreSQL tenant migration notice: {e}")

if __name__ == "__main__":
    asyncio.run(update_all_databases())
