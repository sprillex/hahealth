import requests
import json
import datetime
from datetime import timezone

BASE_URL = "http://localhost:8000"

def verify_macro_tz():
    # 1. Setup User with NY Timezone
    user_name = "tz_macro_test_user"
    password = "password"

    # Create user
    import subprocess
    try:
        subprocess.run(f"./venv/bin/python -m app.cli create-user --name '{user_name}' --password '{password}' --weight 80 --height 180 --unit-system METRIC", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

    # Login
    resp = requests.post(f"{BASE_URL}/auth/token", data={"username": user_name, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Set Timezone
    requests.put(f"{BASE_URL}/api/v1/users/me", json={"timezone": "America/New_York"}, headers=headers)

    # 2. Get API Key for Webhook
    # (Simplified: Just use the API directly since webhook essentially calls service layer,
    # but to fully reproduce we should use webhook.
    # Actually, `log_food` in services.py is what we fixed.)

    # We will use the REST API `/api/v1/nutrition/log` which calls `log_food`.

    # 3. Log Food late at night (NY Time)
    # 11 PM EST = 4 AM UTC Next Day.
    # Current Date in NY: Let's say 2025-12-17
    # We need to simulate that the *server* thinks it is 4 AM UTC (Next Day).
    # BUT `log_food` logic now uses `get_user_local_date` on `datetime.now(utc)`.
    # We can't change `now()`.
    # But we can verify that if we log NOW, it ends up in the correct `DailyLog` bucket and is retrievable via Summary for "Today".

    # Let's create a custom food
    food_data = {"food_name": "Late Night Pizza", "calories": 300, "protein": 15, "fat": 10, "carbs": 40, "source": "MANUAL"}
    requests.post(f"{BASE_URL}/api/v1/nutrition/", json=food_data, headers=headers)

    # Log it
    requests.post(f"{BASE_URL}/api/v1/nutrition/log", json={"food_name": "Late Night Pizza"}, headers=headers)

    # 4. Check Summary for "Today" (User Local)
    # We need to ask for the date corresponding to "Today" in NY.
    # If the fix works, `DailyLog` should be keyed by NY Date.
    # And `Summary` endpoint (using NY Date) should find the `FoodItemLog` (UTC) because of the range conversion.

    # Calculate "Today" in NY
    import zoneinfo
    ny_tz = zoneinfo.ZoneInfo("America/New_York")
    ny_today = datetime.datetime.now(ny_tz).date()
    date_str = ny_today.strftime("%Y-%m-%d")

    print(f"Requesting summary for NY Date: {date_str}")
    summary = requests.get(f"{BASE_URL}/api/v1/log/summary?date_str={date_str}", headers=headers).json()

    print("Summary:", json.dumps(summary, indent=2))

    macros = summary.get("macros", {})
    if macros.get("protein", 0) >= 15:
        print("SUCCESS: Macros found for the correct local date.")
    else:
        print("FAILURE: Macros missing (likely logged to wrong day or query range mismatch).")

if __name__ == "__main__":
    verify_macro_tz()
