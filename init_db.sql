-- PostgreSQL Initialization Script for ERP
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS tenant_1;

-- Tables
CREATE TYPE purchasestatus AS ENUM ('DRAFT', 'COMPLETED', 'CANCELLED');
CREATE TYPE debtstatus AS ENUM ('OPEN', 'PARTIAL', 'PAID', 'OVERDUE');

CREATE TABLE tenants (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	email VARCHAR, 
	tax_id VARCHAR, 
	phone VARCHAR, 
	address VARCHAR, 
	logo_url VARCHAR, 
	primary_color VARCHAR, 
	secondary_color VARCHAR, 
	settings JSONB DEFAULT '{}'::jsonb,
	license_key VARCHAR, 
	subscription_end TIMESTAMP WITH TIME ZONE, 
	parent_id INTEGER, 
	is_active BOOLEAN, 
	modules JSONB DEFAULT '{}'::jsonb, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES tenants (id)
)

;
CREATE INDEX ix_tenants_name ON tenants (name);
CREATE INDEX ix_tenants_id ON tenants (id);
CREATE UNIQUE INDEX ix_tenants_license_key ON tenants (license_key);

CREATE TABLE permissions (
	id SERIAL NOT NULL, 
	code VARCHAR NOT NULL, 
	description VARCHAR, 
	module VARCHAR NOT NULL, 
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_permissions_id ON permissions (id);
CREATE UNIQUE INDEX ix_permissions_code ON permissions (code);

CREATE TABLE categories (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_categories_id ON categories (id);
CREATE INDEX ix_categories_name ON categories (name);
CREATE INDEX ix_categories_tenant_id ON categories (tenant_id);

CREATE TABLE exchange_rate_history (
	id SERIAL NOT NULL, 
	rate FLOAT NOT NULL, 
	provider VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_exchange_rate_history_tenant_id ON exchange_rate_history (tenant_id);
CREATE INDEX ix_exchange_rate_history_id ON exchange_rate_history (id);

CREATE TABLE warehouses (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	address VARCHAR, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_warehouses_name ON warehouses (name);
CREATE INDEX ix_warehouses_tenant_id ON warehouses (tenant_id);
CREATE INDEX ix_warehouses_id ON warehouses (id);

CREATE TABLE cash_registers (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	computer_uid VARCHAR, 
	is_active INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_cash_registers_tenant_id ON cash_registers (tenant_id);
CREATE INDEX ix_cash_registers_id ON cash_registers (id);
CREATE UNIQUE INDEX ix_cash_registers_computer_uid ON cash_registers (computer_uid);

CREATE TABLE customers (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	email VARCHAR, 
	phone VARCHAR, 
	tax_id VARCHAR, 
	address VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_customers_name ON customers (name);
CREATE INDEX ix_customers_id ON customers (id);
CREATE INDEX ix_customers_tenant_id ON customers (tenant_id);

CREATE TABLE tax_rates (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	rate FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_tax_rates_tenant_id ON tax_rates (tenant_id);
CREATE INDEX ix_tax_rates_id ON tax_rates (id);

CREATE TABLE suppliers (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	email VARCHAR, 
	tax_id VARCHAR, 
	phone VARCHAR, 
	address TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE UNIQUE INDEX ix_suppliers_email ON suppliers (email);
CREATE UNIQUE INDEX ix_suppliers_tax_id ON suppliers (tax_id);
CREATE INDEX ix_suppliers_tenant_id ON suppliers (tenant_id);
CREATE INDEX ix_suppliers_id ON suppliers (id);
CREATE INDEX ix_suppliers_name ON suppliers (name);

CREATE TABLE accounts (
	id SERIAL NOT NULL, 
	code VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	type VARCHAR NOT NULL, 
	balance FLOAT, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_accounts_tenant_id ON accounts (tenant_id);
CREATE INDEX ix_accounts_code ON accounts (code);
CREATE INDEX ix_accounts_id ON accounts (id);

CREATE TABLE journal_entries (
	id SERIAL NOT NULL, 
	date TIMESTAMP WITHOUT TIME ZONE, 
	reference VARCHAR, 
	description TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_journal_entries_id ON journal_entries (id);
CREATE INDEX ix_journal_entries_tenant_id ON journal_entries (tenant_id);

CREATE TABLE roles (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	is_system_role BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_roles_tenant_id ON roles (tenant_id);
CREATE INDEX ix_roles_name ON roles (name);
CREATE INDEX ix_roles_id ON roles (id);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR NOT NULL, 
	email VARCHAR, 
	hashed_password VARCHAR NOT NULL, 
	is_active BOOLEAN DEFAULT TRUE, 
	is_superuser BOOLEAN DEFAULT FALSE, 
	modules VARCHAR, 
	role_id INTEGER,
	-- Seguridad: bloqueo por intentos fallidos
	login_attempts INTEGER NOT NULL DEFAULT 0,
	is_locked BOOLEAN NOT NULL DEFAULT FALSE,
	locked_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE SET NULL, 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_tenant_id ON users (tenant_id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_users_is_locked ON users (is_locked);

CREATE TABLE bin_locations (
	id SERIAL NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	code VARCHAR NOT NULL, 
	description VARCHAR, 
	zone VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_bin_locations_code ON bin_locations (code);
CREATE INDEX ix_bin_locations_id ON bin_locations (id);
CREATE INDEX ix_bin_locations_tenant_id ON bin_locations (tenant_id);

CREATE TABLE products (
	id SERIAL NOT NULL, 
	name VARCHAR NOT NULL, 
	sku VARCHAR NOT NULL, 
	description VARCHAR, 
	category_id INTEGER, 
	price FLOAT, 
	cost FLOAT, 
	average_cost FLOAT, 
	track_batches BOOLEAN, 
	track_expiry BOOLEAN, 
	min_stock FLOAT, 
	max_stock FLOAT, 
	unit_of_measure VARCHAR, 
	track_serials BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_products_name ON products (name);
CREATE UNIQUE INDEX ix_products_sku ON products (sku);
CREATE INDEX ix_products_tenant_id ON products (tenant_id);
CREATE INDEX ix_products_id ON products (id);

CREATE TABLE dispatch_notes (
	id SERIAL NOT NULL, 
	source_warehouse_id INTEGER NOT NULL, 
	destination_warehouse_id INTEGER NOT NULL, 
	status VARCHAR, 
	reference VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(destination_warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_dispatch_notes_tenant_id ON dispatch_notes (tenant_id);
CREATE INDEX ix_dispatch_notes_id ON dispatch_notes (id);

CREATE TABLE budgets (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	subtotal FLOAT NOT NULL, 
	tax_total FLOAT NOT NULL, 
	total FLOAT NOT NULL, 
	currency VARCHAR, 
	status VARCHAR, 
	valid_until VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_budgets_tenant_id ON budgets (tenant_id);
CREATE INDEX ix_budgets_id ON budgets (id);

CREATE TABLE purchases (
	id SERIAL NOT NULL, 
	supplier_id INTEGER NOT NULL, 
	status purchasestatus, 
	subtotal FLOAT NOT NULL, 
	tax_total FLOAT NOT NULL, 
	total FLOAT NOT NULL, 
	reference VARCHAR, 
	payment_method VARCHAR, 
	is_accounted BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_purchases_id ON purchases (id);
CREATE INDEX ix_purchases_tenant_id ON purchases (tenant_id);

CREATE TABLE journal_entry_details (
	id SERIAL NOT NULL, 
	journal_entry_id INTEGER NOT NULL, 
	account_id INTEGER NOT NULL, 
	debit FLOAT, 
	credit FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(journal_entry_id) REFERENCES journal_entries (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_journal_entry_details_id ON journal_entry_details (id);
CREATE INDEX ix_journal_entry_details_tenant_id ON journal_entry_details (tenant_id);

CREATE TABLE role_permissions (
	id SERIAL NOT NULL, 
	role_id INTEGER NOT NULL, 
	permission_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	CONSTRAINT uix_role_permission UNIQUE (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE, 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_role_permissions_id ON role_permissions (id);
CREATE INDEX ix_role_permissions_tenant_id ON role_permissions (tenant_id);

CREATE TABLE batches (
	id SERIAL NOT NULL, 
	product_id INTEGER NOT NULL, 
	batch_number VARCHAR NOT NULL, 
	expiry_date TIMESTAMP WITH TIME ZONE, 
	production_date TIMESTAMP WITH TIME ZONE, 
	supplier_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_batches_id ON batches (id);
CREATE INDEX ix_batches_tenant_id ON batches (tenant_id);
CREATE INDEX ix_batches_batch_number ON batches (batch_number);

CREATE TABLE serial_numbers (
	id SERIAL NOT NULL, 
	product_id INTEGER NOT NULL, 
	serial_number VARCHAR NOT NULL, 
	status VARCHAR, 
	warehouse_id INTEGER, 
	bin_location_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(bin_location_id) REFERENCES bin_locations (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_serial_numbers_tenant_id ON serial_numbers (tenant_id);
CREATE INDEX ix_serial_numbers_id ON serial_numbers (id);
CREATE UNIQUE INDEX ix_serial_numbers_serial_number ON serial_numbers (serial_number);

CREATE TABLE dispatch_note_items (
	id SERIAL NOT NULL, 
	dispatch_note_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(dispatch_note_id) REFERENCES dispatch_notes (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_dispatch_note_items_tenant_id ON dispatch_note_items (tenant_id);
CREATE INDEX ix_dispatch_note_items_id ON dispatch_note_items (id);

CREATE TABLE cash_sessions (
	id SERIAL NOT NULL, 
	register_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	opening_time TIMESTAMP WITHOUT TIME ZONE, 
	closing_time TIMESTAMP WITHOUT TIME ZONE, 
	starting_cash FLOAT, 
	expected_cash FLOAT, 
	actual_cash FLOAT, 
	status VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(register_id) REFERENCES cash_registers (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_cash_sessions_id ON cash_sessions (id);
CREATE INDEX ix_cash_sessions_tenant_id ON cash_sessions (tenant_id);

CREATE TABLE budget_items (
	id SERIAL NOT NULL, 
	budget_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity FLOAT NOT NULL, 
	unit_price FLOAT NOT NULL, 
	subtotal FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(budget_id) REFERENCES budgets (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_budget_items_id ON budget_items (id);
CREATE INDEX ix_budget_items_tenant_id ON budget_items (tenant_id);

CREATE TABLE purchase_details (
	id SERIAL NOT NULL, 
	purchase_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity FLOAT NOT NULL, 
	cost_price FLOAT NOT NULL, 
	subtotal FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(purchase_id) REFERENCES purchases (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_purchase_details_id ON purchase_details (id);
CREATE INDEX ix_purchase_details_tenant_id ON purchase_details (tenant_id);

CREATE TABLE refresh_tokens (
	id SERIAL NOT NULL, 
	jti VARCHAR NOT NULL, 
	token VARCHAR NOT NULL, 
	user_id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	revoked BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;
CREATE UNIQUE INDEX ix_refresh_tokens_jti ON refresh_tokens (jti);
CREATE INDEX ix_refresh_tokens_id ON refresh_tokens (id);

CREATE TABLE accounts_payable (
	id SERIAL NOT NULL, 
	purchase_id INTEGER NOT NULL, 
	supplier_id INTEGER NOT NULL, 
	total_amount FLOAT NOT NULL, 
	remaining_amount FLOAT NOT NULL, 
	due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	status debtstatus, 
	notes VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(purchase_id) REFERENCES purchases (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_accounts_payable_id ON accounts_payable (id);
CREATE INDEX ix_accounts_payable_tenant_id ON accounts_payable (tenant_id);

CREATE TABLE stock_movements (
	id SERIAL NOT NULL, 
	product_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	bin_location_id INTEGER, 
	batch_id INTEGER, 
	movement_type VARCHAR NOT NULL, 
	quantity FLOAT NOT NULL, 
	reference VARCHAR, 
	user_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(bin_location_id) REFERENCES bin_locations (id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_stock_movements_id ON stock_movements (id);
CREATE INDEX ix_stock_movements_tenant_id ON stock_movements (tenant_id);

CREATE TABLE stock_summary (
	id SERIAL NOT NULL, 
	product_id INTEGER NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	bin_location_id INTEGER, 
	batch_id INTEGER, 
	quantity FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(bin_location_id) REFERENCES bin_locations (id), 
	FOREIGN KEY(batch_id) REFERENCES batches (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_stock_summary_id ON stock_summary (id);
CREATE INDEX ix_stock_summary_tenant_id ON stock_summary (tenant_id);

CREATE TABLE sales (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	subtotal FLOAT NOT NULL, 
	tax_total FLOAT NOT NULL, 
	total FLOAT NOT NULL, 
	payment_method VARCHAR, 
	currency VARCHAR, 
	exchange_rate FLOAT, 
	cash_session_id INTEGER, 
	is_accounted BOOLEAN, 
	status VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(cash_session_id) REFERENCES cash_sessions (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_sales_id ON sales (id);
CREATE INDEX ix_sales_tenant_id ON sales (tenant_id);

CREATE TABLE sale_details (
	id SERIAL NOT NULL, 
	sale_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity FLOAT NOT NULL, 
	unit_price FLOAT NOT NULL, 
	tax_rate_id INTEGER, 
	subtotal FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sale_id) REFERENCES sales (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(tax_rate_id) REFERENCES tax_rates (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_sale_details_tenant_id ON sale_details (tenant_id);
CREATE INDEX ix_sale_details_id ON sale_details (id);

CREATE TABLE delivery_notes (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	sale_id INTEGER, 
	status VARCHAR, 
	delivery_address VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(sale_id) REFERENCES sales (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_delivery_notes_id ON delivery_notes (id);
CREATE INDEX ix_delivery_notes_tenant_id ON delivery_notes (tenant_id);

CREATE TABLE debit_notes (
	id SERIAL NOT NULL, 
	customer_id INTEGER NOT NULL, 
	reference_invoice_id INTEGER, 
	amount FLOAT NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(reference_invoice_id) REFERENCES sales (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_debit_notes_id ON debit_notes (id);
CREATE INDEX ix_debit_notes_tenant_id ON debit_notes (tenant_id);

CREATE TABLE accounts_receivable (
	id SERIAL NOT NULL, 
	sale_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	total_amount FLOAT NOT NULL, 
	remaining_amount FLOAT NOT NULL, 
	due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	status debtstatus, 
	notes VARCHAR, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sale_id) REFERENCES sales (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_accounts_receivable_tenant_id ON accounts_receivable (tenant_id);
CREATE INDEX ix_accounts_receivable_id ON accounts_receivable (id);

-- ============================================================
-- TABLA: accounts_payable (BUG-07: faltaba en el script original)
-- ============================================================
CREATE TABLE accounts_payable (
	id SERIAL NOT NULL,
	purchase_id INTEGER NOT NULL,
	supplier_id INTEGER NOT NULL,
	total_amount FLOAT NOT NULL,
	remaining_amount FLOAT NOT NULL,
	due_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	status debtstatus,
	notes VARCHAR,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE,
	tenant_id INTEGER NOT NULL,
	created_by_id INTEGER,
	created_by_name VARCHAR,
	updated_by_id INTEGER,
	updated_by_name VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(purchase_id) REFERENCES purchases (id),
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_accounts_payable_tenant_id ON accounts_payable (tenant_id);
CREATE INDEX ix_accounts_payable_id ON accounts_payable (id);

-- ============================================================
-- TABLA: dispatch_notes (BUG-08: faltaba en el script original)
-- ============================================================
CREATE TABLE dispatch_notes (
	id SERIAL NOT NULL,
	source_warehouse_id INTEGER NOT NULL,
	destination_warehouse_id INTEGER NOT NULL,
	status VARCHAR DEFAULT 'PENDING',
	reference VARCHAR,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE,
	tenant_id INTEGER NOT NULL,
	created_by_id INTEGER,
	created_by_name VARCHAR,
	updated_by_id INTEGER,
	updated_by_name VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(source_warehouse_id) REFERENCES warehouses (id),
	FOREIGN KEY(destination_warehouse_id) REFERENCES warehouses (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_dispatch_notes_id ON dispatch_notes (id);
CREATE INDEX ix_dispatch_notes_tenant_id ON dispatch_notes (tenant_id);

-- ============================================================
-- TABLA: dispatch_note_items (BUG-08: faltaba en el script original)
-- ============================================================
CREATE TABLE dispatch_note_items (
	id SERIAL NOT NULL,
	dispatch_note_id INTEGER NOT NULL,
	product_id INTEGER NOT NULL,
	quantity FLOAT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE,
	tenant_id INTEGER NOT NULL,
	created_by_id INTEGER,
	created_by_name VARCHAR,
	updated_by_id INTEGER,
	updated_by_name VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(dispatch_note_id) REFERENCES dispatch_notes (id) ON DELETE CASCADE,
	FOREIGN KEY(product_id) REFERENCES products (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_dispatch_note_items_id ON dispatch_note_items (id);
CREATE INDEX ix_dispatch_note_items_tenant_id ON dispatch_note_items (tenant_id);



CREATE TABLE delivery_note_items (
	id SERIAL NOT NULL, 
	delivery_note_id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	quantity FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(delivery_note_id) REFERENCES delivery_notes (id), 
	FOREIGN KEY(product_id) REFERENCES products (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_delivery_note_items_id ON delivery_note_items (id);
CREATE INDEX ix_delivery_note_items_tenant_id ON delivery_note_items (tenant_id);

CREATE TABLE treasury_payments (
	id SERIAL NOT NULL, 
	ar_id INTEGER, 
	ap_id INTEGER, 
	amount FLOAT NOT NULL, 
	payment_method VARCHAR, 
	reference VARCHAR, 
	payment_date TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ar_id) REFERENCES accounts_receivable (id), 
	FOREIGN KEY(ap_id) REFERENCES accounts_payable (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_treasury_payments_tenant_id ON treasury_payments (tenant_id);
CREATE INDEX ix_treasury_payments_id ON treasury_payments (id);

-- ============================================================
-- TABLA: stock_movements
-- Historial de movimientos de inventario (WMS)
-- ============================================================
CREATE TABLE stock_movements (
	id SERIAL NOT NULL,
	product_id INTEGER NOT NULL,
	warehouse_id INTEGER NOT NULL,
	bin_location_id INTEGER,
	batch_id INTEGER,
	movement_type VARCHAR NOT NULL,
	movement_subtype VARCHAR,
	quantity FLOAT NOT NULL,
	reference VARCHAR,
	document_number VARCHAR,
	notes TEXT,
	user_id INTEGER,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
	updated_at TIMESTAMP WITH TIME ZONE,
	tenant_id INTEGER NOT NULL,
	created_by_id INTEGER,
	created_by_name VARCHAR,
	updated_by_id INTEGER,
	updated_by_name VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(product_id) REFERENCES products (id),
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_stock_movements_id ON stock_movements (id);
CREATE INDEX ix_stock_movements_tenant_id ON stock_movements (tenant_id);
CREATE INDEX ix_stock_movements_product_id ON stock_movements (product_id);
CREATE INDEX ix_stock_movements_warehouse_id ON stock_movements (warehouse_id);
CREATE INDEX ix_stock_movements_movement_type ON stock_movements (movement_type);
CREATE INDEX ix_stock_movements_movement_subtype ON stock_movements (movement_subtype);
CREATE INDEX ix_stock_movements_created_at ON stock_movements (created_at);

-- ============================================================
-- TABLA: system_movements
-- Bitácora universal de TODOS los movimientos del ERP:
-- Cargos, Descargos, Ajustes, Ventas, Compras, Pagos, Asientos
-- ============================================================
CREATE TABLE system_movements (
	id SERIAL NOT NULL,
	tenant_id INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	user_id INTEGER,
	user_name VARCHAR,
	module VARCHAR NOT NULL,
	operation VARCHAR NOT NULL,
	reference_id INTEGER,
	reference_type VARCHAR,
	reference_code VARCHAR,
	product_id INTEGER,
	product_name VARCHAR,
	product_sku VARCHAR,
	warehouse_id INTEGER,
	warehouse_name VARCHAR,
	quantity FLOAT,
	unit VARCHAR,
	amount FLOAT,
	unit_cost FLOAT,
	currency VARCHAR DEFAULT 'VES',
	description TEXT NOT NULL,
	notes TEXT,
	status VARCHAR,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_system_movements_id ON system_movements (id);
CREATE INDEX ix_system_movements_tenant_id ON system_movements (tenant_id);
CREATE INDEX ix_system_movements_module ON system_movements (module);
CREATE INDEX ix_system_movements_operation ON system_movements (operation);
CREATE INDEX ix_system_movements_created_at ON system_movements (created_at);
CREATE INDEX ix_system_movements_product_id ON system_movements (product_id);
CREATE INDEX ix_system_movements_user_id ON system_movements (user_id);

