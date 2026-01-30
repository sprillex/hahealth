from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from app.models import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./health_app.db"

# Create engine with shared cache disabled for potential file swaps (though less critical for sqlite compared to pooling)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_nutrition_table():
    """Checks for missing columns in nutrition_cache and adds them."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table("nutrition_cache"):
            return

        columns = [c["name"] for c in inspector.get_columns("nutrition_cache")]

        # Map of column name -> SQLite type definition
        new_columns = {
            "brand": "VARCHAR",
            "serving_size_unit": "VARCHAR",
            "serving_weight_grams": "FLOAT",
            "serving_volume_ml": "FLOAT",
            "cholesterol": "FLOAT DEFAULT 0.0",
            "total_sugars": "FLOAT DEFAULT 0.0",
            "added_sugars": "FLOAT DEFAULT 0.0",
            "vitamin_d": "FLOAT DEFAULT 0.0",
            "calcium": "FLOAT DEFAULT 0.0",
            "iron": "FLOAT DEFAULT 0.0",
            "potassium": "FLOAT DEFAULT 0.0",
            "health_score": "VARCHAR",
            "health_insight": "VARCHAR",
            "pairing_tip": "VARCHAR"
        }

        with engine.connect() as conn:
            for col, type_def in new_columns.items():
                if col not in columns:
                    print(f"Migrating nutrition_cache: Adding column {col}")
                    conn.execute(text(f"ALTER TABLE nutrition_cache ADD COLUMN {col} {type_def}"))

            # Staple migration
            if "is_staple" not in columns:
                print(f"Migrating nutrition_cache: Adding column is_staple")
                conn.execute(text("ALTER TABLE nutrition_cache ADD COLUMN is_staple BOOLEAN DEFAULT 0"))

            # Shopping List migration
            if "on_shopping_list" not in columns:
                print(f"Migrating nutrition_cache: Adding column on_shopping_list")
                conn.execute(text("ALTER TABLE nutrition_cache ADD COLUMN on_shopping_list BOOLEAN DEFAULT 0"))

            conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")

def migrate_recipe_ingredients_table():
    """Checks for missing columns in recipe_ingredients and adds them."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table("recipe_ingredients"):
            return

        columns = [c["name"] for c in inspector.get_columns("recipe_ingredients")]

        # Map of column name -> SQLite type definition
        new_columns = {
            "unit": "VARCHAR DEFAULT 'serving'"
        }

        with engine.connect() as conn:
            for col, type_def in new_columns.items():
                if col not in columns:
                    print(f"Migrating recipe_ingredients: Adding column {col}")
                    conn.execute(text(f"ALTER TABLE recipe_ingredients ADD COLUMN {col} {type_def}"))
            conn.commit()
    except Exception as e:
        print(f"Recipe Ingredient Migration failed: {e}")

def migrate_users_table():
    """Checks for missing columns in users and adds them."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            return

        columns = [c["name"] for c in inspector.get_columns("users")]

        # Map of column name -> SQLite type definition
        new_columns = {
            "meal_breakfast_start": "TIME DEFAULT '09:00:00'",
            "meal_lunch_start": "TIME DEFAULT '11:00:00'",
            "meal_dinner_start": "TIME DEFAULT '15:00:00'",
            "meal_dinner_end": "TIME DEFAULT '19:00:00'"
        }

        with engine.connect() as conn:
            for col, type_def in new_columns.items():
                if col not in columns:
                    print(f"Migrating users: Adding column {col}")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {type_def}"))
            conn.commit()
    except Exception as e:
        print(f"Users Migration failed: {e}")

def migrate_food_item_logs_table():
    """Checks for missing columns in food_item_logs and adds them."""
    try:
        inspector = inspect(engine)
        if not inspector.has_table("food_item_logs"):
            return

        columns = [c["name"] for c in inspector.get_columns("food_item_logs")]

        # Map of column name -> SQLite type definition
        new_columns = {
            "planned_quantity": "FLOAT DEFAULT 0.0"
        }

        with engine.connect() as conn:
            for col, type_def in new_columns.items():
                if col not in columns:
                    print(f"Migrating food_item_logs: Adding column {col}")
                    conn.execute(text(f"ALTER TABLE food_item_logs ADD COLUMN {col} {type_def}"))
            conn.commit()
    except Exception as e:
        print(f"Food Item Logs Migration failed: {e}")

def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_nutrition_table()
    migrate_recipe_ingredients_table()
    migrate_users_table()
    migrate_food_item_logs_table()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def dispose_engine():
    """Closes all connections in the pool."""
    engine.dispose()
