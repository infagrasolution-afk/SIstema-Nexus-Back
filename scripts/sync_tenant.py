import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import Base
from app.domain import *  # This loads all models into Base.metadata

tenant_db = os.path.join("tenant_data", "tenant_1.db")
# In Windows paths might be different, let's just use N_M_C_1.db
tenant_db = "N_M_C_1.db"

if not os.path.exists(tenant_db):
    print(f"Error: {tenant_db} not found")
    sys.exit(1)

conn = sqlite3.connect(tenant_db)
cursor = conn.cursor()

# Get all tables in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
db_tables = {row[0] for row in cursor.fetchall()}

for table_name, table in Base.metadata.tables.items():
    if table_name not in db_tables:
        continue
    
    # Get columns currently in the database
    cursor.execute(f"PRAGMA table_info({table_name})")
    db_columns = {row[1] for row in cursor.fetchall()}
    
    # Check for missing columns
    for column in table.columns:
        if column.name not in db_columns:
            # Add missing column
            from sqlalchemy.dialects import sqlite
            col_type = column.type.compile(dialect=sqlite.dialect())
            # Default to NULL if no default is provided
            print(f"Adding missing column {column.name} to {table_name}")
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}")
            except Exception as e:
                print(f"Failed to add {column.name} to {table_name}: {e}")

conn.commit()
conn.close()
print("Tenant DB sync complete.")
