import sqlite3

def migrate():
    print("Migrating database for Time Windows...")
    conn = sqlite3.connect("health_app.db")
    cursor = conn.cursor()

    # 1. Add User Columns
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN window_morning_start TIME DEFAULT '06:00:00'")
        print("Added window_morning_start to users")
    except sqlite3.OperationalError:
        print("window_morning_start already exists in users")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN window_afternoon_start TIME DEFAULT '12:00:00'")
        print("Added window_afternoon_start to users")
    except sqlite3.OperationalError:
        print("window_afternoon_start already exists in users")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN window_evening_start TIME DEFAULT '17:00:00'")
        print("Added window_evening_start to users")
    except sqlite3.OperationalError:
        print("window_evening_start already exists in users")

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN window_bedtime_start TIME DEFAULT '21:00:00'")
        print("Added window_bedtime_start to users")
    except sqlite3.OperationalError:
        print("window_bedtime_start already exists in users")

    # 2. Add Medication Columns
    try:
        cursor.execute("ALTER TABLE medications ADD COLUMN schedule_morning BOOLEAN DEFAULT 0")
        print("Added schedule_morning to medications")
    except sqlite3.OperationalError:
        print("schedule_morning already exists in medications")

    try:
        cursor.execute("ALTER TABLE medications ADD COLUMN schedule_afternoon BOOLEAN DEFAULT 0")
        print("Added schedule_afternoon to medications")
    except sqlite3.OperationalError:
        print("schedule_afternoon already exists in medications")

    try:
        cursor.execute("ALTER TABLE medications ADD COLUMN schedule_evening BOOLEAN DEFAULT 0")
        print("Added schedule_evening to medications")
    except sqlite3.OperationalError:
        print("schedule_evening already exists in medications")

    try:
        cursor.execute("ALTER TABLE medications ADD COLUMN schedule_bedtime BOOLEAN DEFAULT 0")
        print("Added schedule_bedtime to medications")
    except sqlite3.OperationalError:
        print("schedule_bedtime already exists in medications")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
