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
            conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")

def init_db():
    Base.metadata.create_all(bind=engine)
    migrate_nutrition_table()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def dispose_engine():
    """Closes all connections in the pool."""
    engine.dispose()
