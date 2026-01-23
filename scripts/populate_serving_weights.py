import sys
import os
import re
import signal

# Add the parent directory to sys.path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import NutritionCache

def signal_handler(sig, frame):
    print("\nExiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def process_foods(session, input_func=input):
    """
    Iterates through foods with missing serving_weight_grams and prompts the user.
    input_func is allowed to be injected for testing purposes.
    """
    # Query for foods where serving_weight_grams is None
    # Using is_(None) is the correct SQLAlchemy syntax for NULL checks
    foods = session.query(NutritionCache).filter(NutritionCache.serving_weight_grams.is_(None)).all()

    print(f"Found {len(foods)} foods with missing serving weights.")

    # Regex to match grams, e.g., "185g", "(113g)", "12.5g"
    # Captures the number part.
    regex = re.compile(r'\(?(\d+(?:\.\d+)?)\s*g\)?', re.IGNORECASE)

    for i, food in enumerate(foods):
        print(f"\n[{i+1}/{len(foods)}] Food: {food.food_name}")
        print(f"Serving Unit (Text): {food.serving_size_unit}")

        extracted_val = None
        if food.serving_size_unit:
            match = regex.search(food.serving_size_unit)
            if match:
                extracted_val = float(match.group(1))

        while True:
            if extracted_val is not None:
                prompt = f"Extracted {extracted_val}g. Is this correct? (y/n/[number]): "
                user_input = input_func(prompt).strip().lower()

                if user_input == 'y':
                    food.serving_weight_grams = extracted_val
                    session.commit()
                    print(f"Updated '{food.food_name}' with {extracted_val}g.")
                    break
                elif user_input == 'n':
                    print("Skipped.")
                    break
                else:
                    # Try to parse as number
                    try:
                        val = float(user_input)
                        food.serving_weight_grams = val
                        session.commit()
                        print(f"Updated '{food.food_name}' with {val}g.")
                        break
                    except ValueError:
                        print("Invalid input. Please enter 'y', 'n', or a number.")
            else:
                prompt = "No grams extracted. Enter value in grams or 'n' to skip: "
                user_input = input_func(prompt).strip().lower()
                if user_input == 'n':
                    print("Skipped.")
                    break
                else:
                    try:
                        val = float(user_input)
                        food.serving_weight_grams = val
                        session.commit()
                        print(f"Updated '{food.food_name}' with {val}g.")
                        break
                    except ValueError:
                        print("Invalid input. Please enter 'n' or a number.")

def main():
    session = SessionLocal()
    try:
        process_foods(session)
    finally:
        session.close()

if __name__ == "__main__":
    main()
