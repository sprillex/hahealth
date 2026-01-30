#!/usr/bin/env python3
import sys
import os

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.getcwd())

try:
    from app.database import SessionLocal
    from app.models import NutritionCache
    from sqlalchemy import or_
except ImportError as e:
    print("\nError: Could not import application modules.")
    print(f"Details: {e}")
    print("Please ensure you have installed the requirements using:")
    print("  pip install -r requirements.txt")
    print("And that you are running this script from the project root directory.\n")
    sys.exit(1)

def main():
    session = SessionLocal()
    try:
        # Query for foods where health_insight is missing (None, empty string, or "NaN")
        foods = session.query(NutritionCache).filter(
            or_(
                NutritionCache.health_insight.is_(None),
                NutritionCache.health_insight == "",
                NutritionCache.health_insight == "NaN"
            )
        ).all()

        print(f"Found {len(foods)} foods with missing health insights.\n")

        for food in foods:
            upc = food.barcode if food.barcode else "N/A"
            print(f"Name: {food.food_name}, UPC: {upc}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main()
