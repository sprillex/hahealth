import sqlite3

def add_exercise_table():
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()

    try:
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
        print("Table 'exercise_logs' checked/created successfully.")

        # Check if index exists, if not create it
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_exercise_logs_user_id ON exercise_logs (user_id)")

    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_exercise_table()
