import sqlite3
import os

def migrate():
    db_path = 'master.db'
    if not os.path.exists(db_path):
        db_path = 'Backend/master.db'
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(tenants)")
    cols = [row[1] for row in cursor.fetchall()]
    
    if 'primary_color' not in cols:
        print("Adding primary_color...")
        cursor.execute("ALTER TABLE tenants ADD COLUMN primary_color VARCHAR DEFAULT '#2563eb'")
    
    if 'secondary_color' not in cols:
        print("Adding secondary_color...")
        cursor.execute("ALTER TABLE tenants ADD COLUMN secondary_color VARCHAR DEFAULT '#64748b'")
        
    if 'settings' not in cols:
        print("Adding settings...")
        cursor.execute("ALTER TABLE tenants ADD COLUMN settings JSON DEFAULT '{}'")
        
    conn.commit()
    conn.close()
    print("Migration successful")

if __name__ == "__main__":
    migrate()
