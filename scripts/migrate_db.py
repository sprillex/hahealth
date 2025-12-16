import sqlite3

def add_column():
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN unit_system VARCHAR DEFAULT 'METRIC'")
        print("Column 'unit_system' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Error (column might already exist): {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_column()
