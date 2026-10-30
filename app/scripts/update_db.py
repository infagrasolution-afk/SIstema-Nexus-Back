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
ALTER TABLE products ADD COLUMN IF NOT EXISTS tax_exempt BOOLEAN DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(18, 4) DEFAULT 16.0000;
ALTER TABLE products ADD COLUMN IF NOT EXISTS margin_percent NUMERIC(18, 4) DEFAULT 30.0000;
DO $$ BEGIN
    ALTER TABLE products ALTER COLUMN price TYPE NUMERIC(18, 4) USING price::numeric(18, 4);
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
"""

async def update_all_databases():
    print("Updating Master Database...")
    async with master_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    print("Running automatic database branding migration...")
    try:
        async with MasterSessionLocal() as session:
            await session.execute(text("UPDATE tenants SET name = 'APEX MASTER CORP' WHERE id = 1"))
            await session.execute(text("UPDATE tenants SET email = 'infagrasolution@gmail.com' WHERE id = 1"))
            await session.execute(text("UPDATE tenants SET name = 'DEMO - APEX ERP' WHERE name = 'DEMO - NEXUS ERP'"))
            await session.execute(text("UPDATE tenants SET email = 'demo@apexerp.com' WHERE email = 'demo@nexuserp.com'"))
            await session.execute(text("UPDATE users SET email = 'infagrasolution@gmail.com' WHERE username = 'admin'"))
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
                schema_name = f"tenant_{tenant.id}"
                print(f"Ensuring schema, tables and columns for Tenant {tenant.id} ({tenant.name})...")
                
                # 1. Crear esquema si no existe
                async with master_engine.begin() as conn:
                    await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
                
                # 2. Crear tablas nuevas con Base.metadata.create_all
                engine = get_tenant_engine(tenant.id)
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                    
                    # 3. Aplicar migraciones idempotentes de columnas y tipos NUMERIC(18,4)
                    try:
                        await conn.execute(text(TENANT_SCHEMA_MIGRATIONS))
                    except Exception as mig_err:
                        print(f"Migration script notice for Tenant {tenant.id}: {mig_err}")
                        
        print("PostgreSQL tenant databases and schemas updated successfully!")
    except Exception as e:
        print(f"PostgreSQL tenant migration notice: {e}")

if __name__ == "__main__":
    asyncio.run(update_all_databases())
