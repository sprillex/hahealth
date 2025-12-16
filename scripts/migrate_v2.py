import sqlite3

def migrate_v2():
    conn = sqlite3.connect('health_app.db')
    cursor = conn.cursor()

    # User Table Updates
    user_cols = [
        ("birth_year", "INTEGER"),
        ("gender", "VARCHAR"),
        ("goal_weight_kg", "FLOAT"),
        ("calorie_goal", "INTEGER")
    ]

    for col, type_ in user_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {type_}")
            print(f"Added {col} to users.")
        except sqlite3.OperationalError:
            print(f"Skipping {col} (likely exists).")

    # Nutrition Table Updates
    nut_cols = [
        ("fat", "FLOAT DEFAULT 0"),
        ("carbs", "FLOAT DEFAULT 0")
    ]

    for col, type_ in nut_cols:
        try:
            cursor.execute(f"ALTER TABLE nutrition_cache ADD COLUMN {col} {type_}")
            print(f"Added {col} to nutrition_cache.")
        except sqlite3.OperationalError:
            print(f"Skipping {col} (likely exists).")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate_v2()
