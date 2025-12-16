import sqlite3
import os

def migrate_all():
    db_path = 'health_app.db'
    if not os.path.exists(db_path):
        print("Database not found. It will be created when you run the app.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

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
        ("carbs", "FLOAT DEFAULT 0")
    ]
    for col, type_ in nut_cols:
        try:
            cursor.execute(f"ALTER TABLE nutrition_cache ADD COLUMN {col} {type_}")
            print(f" - Added {col} to nutrition_cache.")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()
    print("Migrations complete.")

if __name__ == "__main__":
    migrate_all()
