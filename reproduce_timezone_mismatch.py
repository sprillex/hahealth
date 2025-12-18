import datetime
import zoneinfo
import sqlite3
import requests
import time

def reproduce_tz_mismatch():
    # 1. Setup User
    base_url = "http://localhost:8000"
    user = "tz_macro_test"
    password = "password"

    # Create user via CLI (faster than API)
    import subprocess
    try:
        subprocess.run(f"./venv/bin/python -m app.cli create-user --name {user} --password {password} --weight 80 --height 180 --unit-system METRIC", shell=True, check=True, stdout=subprocess.DEVNULL)
    except:
        pass # Exists

    # Login
    resp = requests.post(f"{base_url}/auth/token", data={"username": user, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set Timezone to America/New_York (UTC-5)
    requests.put(f"{base_url}/api/v1/users/me", json={"timezone": "America/New_York"}, headers=headers)

    # 2. Log Food at specific UTC time
    # Target: 2025-12-17 23:00:00 EST -> 2025-12-18 04:00:00 UTC
    # If Server Local is UTC, date.today() will be 2025-12-18 (if running after 00:00 UTC).
    # If Server Local is UTC, log_food will create DailyLog for 2025-12-18.
    # The user considers this "Today" (2025-12-17).
    # If user requests summary for 2025-12-17, they expect to see it.

    # We will simulate this by forcing a FoodItemLog directly via DB to control timestamp,
    # OR create a custom endpoint/webhook that accepts timestamp for food.
    # The existing webhook accepts timestamp? No, FOOD_LOG payload: `barcode`, `food_name`, etc. No timestamp.
    # `log_food` in services.py uses `datetime.utcnow()`.

    # So we MUST modify `log_food` logic or `get_daily_summary` logic.
    # The issue is that `log_food` writes `DailyLog` based on `date.today()`.

    print("Reproduction script: Cannot easily force timestamp via API. Will rely on analysis.")

if __name__ == "__main__":
    reproduce_tz_mismatch()
