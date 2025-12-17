import datetime
from sqlalchemy.orm import Session
from app import models, services
import zoneinfo

def verify_timezone_logic():
    # Setup Logic
    # 1. Create User with specific Timezone (America/New_York)
    # 2. Define Morning Window as 06:00
    # 3. Log a Dose at 02:00 UTC (which is 21:00 or 22:00 Previous Day in NY)
    # 4. Run Compliance Report
    # 5. Assert it counts as 'Bedtime' of previous day? Or at least DOES NOT count as 'Morning' of current day.

    # Actually, verifying the 'Bedtime' wrap logic specifically is complex without creating full DB mock.
    # I'll rely on inspecting the `get_window_and_date` function behavior by importing it if I can,
    # but it's nested in `calculate_compliance_report`.

    # I will verify via end-to-end test using the API if possible, or just unit test the logic if I extract it.
    # Since I modified `services.py`, I can test `calculate_compliance_report` if I mock the DB session.
    # Too complex to mock DB session quickly.

    # I'll create a script that interacts with the running app.

    import requests
    import json

    BASE_URL = "http://localhost:8000"

    # 1. Create User
    # Using CLI or API? API requires token. CLI is easier.
    import subprocess
    user_name = "tz_tester"
    try:
        subprocess.run(f"./venv/bin/python -m app.cli create-user --name '{user_name}' --password 'pass' --weight 70 --height 170", shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass # Exists

    # Login
    resp = requests.post(f"{BASE_URL}/auth/token", data={"username": user_name, "password": "pass"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update Profile Timezone to 'America/New_York'
    requests.put(f"{BASE_URL}/api/v1/users/me", json={"timezone": "America/New_York"}, headers=headers)

    # Create Medication with Morning Schedule
    med_data = {
        "name": "MorningMed",
        "frequency": "Daily",
        "type": "OTC",
        "current_inventory": 100,
        "refills_remaining": 5,
        "schedule_morning": True
    }
    requests.post(f"{BASE_URL}/api/v1/medications/", json=med_data, headers=headers)

    # Log Dose at 09:00 UTC.
    # NY is UTC-5 (Standard) or UTC-4 (DST).
    # 09:00 UTC = 04:00 or 05:00 NY.
    # Morning starts at 06:00 (default).
    # So 04:00/05:00 < 06:00.
    # This should be classified as "Bedtime" of previous day (or Evening/Late Night).
    # It should NOT count as "Morning" for today.
    # If logic was using UTC (09:00), it WOULD count as Morning (09:00 > 06:00).

    # Current Date (UTC)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Force time to 09:00 UTC today
    test_time = now_utc.replace(hour=9, minute=0, second=0, microsecond=0)

    # Use webhook to log specific timestamp (easiest way to force timestamp)
    # Need API Key
    # Manually extract key? Or just use Python to inject into DB?
    # Actually, `services.py` `log_dose` takes `timestamp_taken`.
    # But `webhook` is the only one exposing `timestamp` input directly for meds?
    # Check `medication.py` router. It doesn't seem to have a log-dose endpoint with timestamp?
    # Ah, `webhook` is the way.

    # Get API Key
    import sqlite3
    conn = sqlite3.connect('health_app.db')
    c = conn.cursor()
    c.execute(f"SELECT user_id FROM users WHERE name='{user_name}'")
    uid = c.fetchone()[0]
    conn.close()

    cmd_key = f"./venv/bin/python -m app.cli create-apikey --user-id {uid} --name 'TZ_Test'"
    res = subprocess.run(cmd_key, shell=True, capture_output=True, text=True)
    secret_key = None
    for line in res.stdout.split('\n'):
        if "SECRET KEY:" in line:
            secret_key = line.split("SECRET KEY:")[1].strip()

    # Log Dose via Webhook
    payload = {
        "data_type": "MEDICATION_TAKEN",
        "payload": {
            "med_name": "MorningMed",
            "timestamp": test_time.isoformat()
        }
    }
    requests.post(f"{BASE_URL}/api/webhook/health", json=payload, headers={"X-Webhook-Secret": secret_key, "Content-Type": "application/json"})

    # Check Compliance Report
    # Since we logged a dose that is 4/5 AM Local time, and Morning starts at 6 AM.
    # It should NOT match Morning window for Today.
    # Compliance for MorningMed (Scheduled Morning) should be 0/1 (0%).
    # If it ignored TZ and used 9 AM, it would match Morning (6-12), so 1/1 (100%).

    # Wait for processing? Sync.

    rep = requests.get(f"{BASE_URL}/api/v1/log/reports/compliance", headers=headers)
    data = rep.json()

    print("Report Data:", json.dumps(data, indent=2))

    # Find MorningMed
    med_stat = next((m for m in data['medications'] if m['name'] == "MorningMed"), None)
    if not med_stat:
        print("Med not found in report")
        return

    print(f"Compliance for MorningMed: {med_stat['taken']} / {med_stat['expected']}")

    # Logic Verification:
    # 09:00 UTC = 04:00 EST.
    # Window Morning starts 06:00.
    # 04:00 < 06:00. It is BEFORE Morning.
    # Logic in `calculate_compliance_report`:
    # If t < first_window (Morning), matched_window = last_window (Bedtime), date = prev_day.
    # So it counts as Bedtime Yesterday.
    # "MorningMed" is only scheduled for "Morning".
    # So it should NOT count as taken for "Morning" today.
    # Expected: 1 (for today). Taken: 0 (for today).
    # Result: 0/1.

    # If Timezone Logic WAS NOT working (using UTC 09:00):
    # 09:00 >= 06:00. Matched = Morning. Date = Today.
    # Result: 1/1.

    if med_stat['taken'] == 0:
        print("SUCCESS: Timezone logic correctly shifted 09:00 UTC to 04:00/05:00 Local (Before Morning).")
    else:
        print("FAILURE: Timezone logic failed (or DST made it > 6am?)")

if __name__ == "__main__":
    verify_timezone_logic()
