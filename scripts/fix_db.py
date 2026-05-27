import sqlite3
import os

def fix():
    db_path = 'master.db'
    if not os.path.exists(db_path):
        # Intentar en el directorio actual si no se encuentra
        db_path = 'Backend/master.db'
        if not os.path.exists(db_path):
            print(f"Error: master.db no encontrado en el directorio raíz ni en Backend/")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"--- Iniciando reparación de {db_path} ---")

    # 1. Asegurar columnas de auditoría y roles en 'users'
    cols_to_add_users = [
        ('role_id', 'INTEGER'),
        ('created_by_id', 'INTEGER'),
        ('created_by_name', 'VARCHAR'),
        ('updated_by_id', 'INTEGER'),
        ('updated_by_name', 'VARCHAR')
    ]
    
    cursor.execute("PRAGMA table_info(users)")
    existing_users_cols = [row[1] for row in cursor.fetchall()]
    
    for col_name, col_type in cols_to_add_users:
        if col_name not in existing_users_cols:
            print(f"Añadiendo {col_name} a users...")
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Error añadiendo {col_name}: {e}")

    # 2. Crear tablas de RBAC si no existen
    print("Creando tablas de Roles y Permisos...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR NOT NULL,
        description VARCHAR,
        is_system_role BOOLEAN DEFAULT 0,
        tenant_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,
        created_by_id INTEGER,
        created_by_name VARCHAR,
        updated_by_id INTEGER,
        updated_by_name VARCHAR
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code VARCHAR NOT NULL UNIQUE,
        description VARCHAR,
        module VARCHAR NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id INTEGER NOT NULL,
        permission_id INTEGER NOT NULL,
        tenant_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(role_id) REFERENCES roles(id),
        FOREIGN KEY(permission_id) REFERENCES permissions(id)
    )
    """)

    # 3. Marcar la migración como completada en Alembic
    print("Sincronizando con Alembic...")
    cursor.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
    cursor.execute("DELETE FROM alembic_version")
    cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('6cde1e6de3ef')")

    # 4. Crear un rol de Super Admin inicial si no hay roles
    cursor.execute("SELECT count(*) FROM roles WHERE name = 'Super Admin'")
    if cursor.fetchone()[0] == 0:
        print("Creando rol Super Admin inicial...")
        cursor.execute("INSERT INTO roles (name, description, is_system_role, tenant_id) VALUES ('Super Admin', 'Acceso total al sistema', 1, 1)")
        role_id = cursor.lastrowid
        cursor.execute("UPDATE users SET role_id = ? WHERE username = 'admin'", (role_id,))

    conn.commit()
    conn.close()
    print("--- Reparación completada con éxito ---")

if __name__ == "__main__":
    fix()
