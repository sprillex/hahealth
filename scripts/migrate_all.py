import sqlite3
import os

def migrate_all():
    db_path = 'health_app.db'
    if not os.path.exists(db_path):
        print("Database not found. It will be created when you run the app.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]

    print("Running migrations...")

    # 1. Unit System (v1)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN unit_system VARCHAR DEFAULT 'METRIC'")
        print(" - Added unit_system to users.")
    except sqlite3.OperationalError:
        pass # Already exists

    # 2. Exercise Logs (v1.5)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercise_logs (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            activity_type VARCHAR,
            duration_minutes FLOAT,
            calories_burned FLOAT,
            timestamp DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_exercise_logs_user_id ON exercise_logs (user_id)")
    print(" - Checked exercise_logs table.")

    # 3. Profile & Nutrition (v2)
    user_cols = [
        ("birth_year", "INTEGER"),
        ("gender", "VARCHAR"),
        ("goal_weight_kg", "FLOAT"),
        ("calorie_goal", "INTEGER")
    ]
    for col, type_ in user_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {type_}")
            print(f" - Added {col} to users.")
        except sqlite3.OperationalError:
            pass

    nut_cols = [
        ("fat", "FLOAT DEFAULT 0"),
        ("carbs", "FLOAT DEFAULT 0"),
        ("fiber", "FLOAT DEFAULT 0")
    ]
    for col, type_ in nut_cols:
        try:
            cursor.execute(f"ALTER TABLE nutrition_cache ADD COLUMN {col} {type_}")
            print(f" - Added {col} to nutrition_cache.")
        except sqlite3.OperationalError:
            pass

    # 4. Admin & System Config
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        print(" - Added is_admin to users.")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        print(" - Checked system_config table.")
    except sqlite3.OperationalError:
        pass

    # 5. Time Windows & Schedules
    window_cols = [
        ("window_morning_start", "TIME DEFAULT '06:00:00'"),
        ("window_afternoon_start", "TIME DEFAULT '12:00:00'"),
        ("window_evening_start", "TIME DEFAULT '17:00:00'"),
        ("window_bedtime_start", "TIME DEFAULT '21:00:00'")
    ]
    for col, type_ in window_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {type_}")
            print(f" - Added {col} to users.")
        except sqlite3.OperationalError:
            pass

    med_cols = [
        ("schedule_morning", "BOOLEAN DEFAULT 0"),
        ("schedule_afternoon", "BOOLEAN DEFAULT 0"),
        ("schedule_evening", "BOOLEAN DEFAULT 0"),
        ("schedule_bedtime", "BOOLEAN DEFAULT 0")
    ]
    for col, type_ in med_cols:
        try:
            cursor.execute(f"ALTER TABLE medications ADD COLUMN {col} {type_}")
            print(f" - Added {col} to medications.")
        except sqlite3.OperationalError:
            pass

    # 6. Timezone
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN timezone VARCHAR DEFAULT 'UTC'")
        print(" - Added timezone to users.")
    except sqlite3.OperationalError:
        pass

    # 7. Allergies & Vaccinations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allergies (
            allergy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            allergen VARCHAR,
            reaction VARCHAR,
            severity VARCHAR,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_allergies_user_id ON allergies (user_id)")
    print(" - Checked allergies table.")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vaccinations (
            vaccine_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            vaccine_type VARCHAR,
            date_administered DATE,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_vaccinations_user_id ON vaccinations (user_id)")
    print(" - Checked vaccinations table.")

    # 8. Date of Birth
    if "users" in existing_tables:
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if "date_of_birth" not in columns:
            print("Adding 'date_of_birth' column to 'users' table...")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN date_of_birth DATE")
                # Migrate birth_year to date_of_birth (Jan 1st)
                print("Migrating birth_year data...")
                cursor.execute("UPDATE users SET date_of_birth = printf('%d-01-01', birth_year) WHERE birth_year IS NOT NULL")
            except sqlite3.OperationalError as e:
                print(f"Error adding column: {e}")

    conn.commit()
    conn.close()
    print("All migrations complete.")

if __name__ == "__main__":
    migrate_all()
