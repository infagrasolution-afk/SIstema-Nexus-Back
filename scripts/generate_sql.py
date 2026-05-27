import sys
import os
from sqlalchemy import create_mock_engine
from sqlalchemy.schema import CreateSchema

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base
from app.domain import *  # Import all models

def generate_sql():
    output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "init_db.sql")
    
    with open(output_file, 'w') as f:
        f.write("-- PostgreSQL Initialization Script for ERP\n")
        f.write("CREATE SCHEMA IF NOT EXISTS public;\n")
        f.write("CREATE SCHEMA IF NOT EXISTS tenant_1;\n\n")
        
        def dump(sql, *multiparams, **params):
            f.write(str(sql.compile(dialect=engine.dialect)) + ";\n")
            
        engine = create_mock_engine('postgresql://', dump)
        
        # We need to render the tables. Note that some are in public and some in tenant.
        # But for the initial script, we can just create everything in public, and then the app will handle tenant schemas.
        # Wait, if we use schemas in the app, the app's Base.metadata.create_all will create them in the current search_path.
        
        f.write("-- Tables\n")
        Base.metadata.create_all(engine, checkfirst=False)
        
    print(f"SQL script generated at {output_file}")

if __name__ == "__main__":
    generate_sql()
