from datetime import date
from datetime import timedelta
import pytest

def get_auth_token(client):
    # Try login first
    response = client.post(
        "/auth/token",
        data={"username": "meduser", "password": "medpassword"},
    )
    if response.status_code == 200:
        return response.json()["access_token"]

    # If failed, try creating user then login
    client.post(
        "/api/v1/users/",
        json={"name": "meduser", "password": "medpassword", "weight_kg": 70, "height_cm": 175},
    )
    response = client.post(
        "/auth/token",
        data={"username": "meduser", "password": "medpassword"},
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_allergies(client):
    token = get_auth_token(client)
    assert token is not None, "Failed to get auth token"
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    response = client.post(
        "/api/v1/medical/allergies",
        json={"allergen": "Peanuts", "reaction": "Hives", "severity": "Moderate"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["allergen"] == "Peanuts"
    id = data["allergy_id"]

    # Get List
    response = client.get("/api/v1/medical/allergies", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Update
    response = client.put(
        f"/api/v1/medical/allergies/{id}",
        json={"allergen": "Peanuts", "reaction": "Anaphylaxis", "severity": "Severe"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["severity"] == "Severe"

    # Delete
    response = client.delete(f"/api/v1/medical/allergies/{id}", headers=headers)
    assert response.status_code == 204

    response = client.get("/api/v1/medical/allergies", headers=headers)
    assert len(response.json()) == 0

def test_vaccinations(client):
    token = get_auth_token(client)
    assert token is not None
    headers = {"Authorization": f"Bearer {token}"}

    today = date.today()

    # Log Flu Shot
    response = client.post(
        "/api/v1/medical/vaccinations",
        json={"vaccine_type": "Influenza", "date_administered": str(today)},
        headers=headers
    )
    assert response.status_code == 200

    # Log Old Tdap - Safe calculation
    try:
        old_date = today.replace(year=today.year - 11)
    except ValueError:
        # Handle leap year case (Feb 29 -> Feb 28)
        old_date = today.replace(year=today.year - 11, day=28)

    response = client.post(
        "/api/v1/medical/vaccinations",
        json={"vaccine_type": "Tdap", "date_administered": str(old_date)},
        headers=headers
    )
    assert response.status_code == 200

    # Get Report
    response = client.get("/api/v1/medical/reports/vaccinations", headers=headers)
    assert response.status_code == 200
    report = response.json()

    # Check Flu
    flu = next(r for r in report if r["vaccine_type"] == "Influenza")
    assert flu["status"] == "Up to Date"

    # Check Tdap
    tdap = next(r for r in report if "Tdap" in r["vaccine_type"])
    assert tdap["status"] == "Overdue"
