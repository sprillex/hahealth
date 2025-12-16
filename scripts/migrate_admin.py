import sqlite3

def migrate():
    print("Migrating database for Admin features...")
    conn = sqlite3.connect("health_app.db")
    cursor = conn.cursor()

    # 1. Add is_admin to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        print("Added is_admin to users")
    except sqlite3.OperationalError:
        print("is_admin already exists in users")

    # 2. Create SystemConfig table
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        print("Created system_config table")
    except sqlite3.OperationalError as e:
        print(f"Error creating system_config: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
