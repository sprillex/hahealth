import requests
import json

BASE_URL = "http://localhost:8000"

def verify_macros():
    # 1. Login
    resp = requests.post(f"{BASE_URL}/auth/token", data={"username": "johndoe", "password": "securepass"})
    if resp.status_code != 200:
        print("Login failed")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Log Food using a known barcode (e.g., Nutella or Coca Cola)
    # Using a fake/test barcode that OpenFoodFacts might not have, so I should mock it or use a real one.
    # Coca Cola 330ml: 5449000000996 (or similar)
    # Let's try to log a custom manual food first to ensure aggregation works.

    # Create Custom Food
    food_data = {
        "food_name": "Test Macro Food",
        "calories": 100,
        "protein": 10,
        "fat": 5,
        "carbs": 20,
        "fiber": 2,
        "source": "MANUAL"
    }

    # Post to /api/v1/nutrition/
    resp = requests.post(f"{BASE_URL}/api/v1/nutrition/", json=food_data, headers=headers)
    if resp.status_code not in [200, 422]: # 422 if I messed schema
        print(f"Create food failed: {resp.text}")

    # If 422, let's fix schema usage

    # Log it
    log_data = {
        "food_name": "Test Macro Food",
        "meal_id": "Snack",
        "serving_size": 2, # Double the macros
        "quantity": 1
    }
    resp = requests.post(f"{BASE_URL}/api/v1/nutrition/log", json=log_data, headers=headers)
    print(f"Log response: {resp.status_code} {resp.text}")

    # 3. Check Summary
    summary = requests.get(f"{BASE_URL}/api/v1/log/summary", headers=headers).json()
    print("Summary:", json.dumps(summary, indent=2))

    macros = summary.get("macros", {})

    # Expected: 2 * 10 = 20g protein
    if macros.get("protein") == 20:
        print("SUCCESS: Macros are aggregating correctly.")
    else:
        print(f"FAILURE: Expected 20g protein, got {macros.get('protein')}")

if __name__ == "__main__":
    verify_macros()
