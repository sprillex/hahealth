import pytest
from app import models

def test_daily_summary_extended_nutrients(client, session):
    # 1. Create User
    user_data = {"name": "test_summary_user", "password": "password", "weight_kg": 70, "height_cm": 170}
    response = client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 200

    # Login
    login_data = {"username": "test_summary_user", "password": "password"}
    response = client.post("/auth/token", data=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Log Food via API V2 (Full integration test)
    # This matches what the verification script does.

    payload = {
        "quantity": 2.0,
        "timestamp": None,
        "meal": "Lunch",
        "variables": {
            "Extended Nutrients Test Food": {
                "metadata": {
                    "name": "Extended Nutrients Test Food",
                    "brand": "TestBrand",
                    "upc": "9999990001"
                },
                "macros": {
                    "calories": 100.0,
                    "protein_g": 10.0,
                    "fat_g": 5.0,
                    "carbs_g": 20.0,
                    "fiber_g": 0.0,
                    "sodium_mg": 0.0,
                    "cholesterol_mg": 50.0,
                    "total_sugars_g": 15.0,
                    "added_sugars_g": 5.0
                },
                "micros": {
                    "vit_d_mcg": 10.0,
                    "calcium_mg": 200.0,
                    "iron_mg": 5.0,
                    "potassium_mg": 300.0
                }
            }
        }
    }

    response = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert response.status_code == 200

    # 4. Get Summary
    response = client.get("/api/v1/log/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()

    macros = data["macros"]

    # 5. Assertions (Should be 2x the food values)
    assert macros["protein"] == 20.0
    assert macros["cholesterol"] == 100.0
    assert macros["total_sugars"] == 30.0
    assert macros["added_sugars"] == 10.0
    assert macros["vitamin_d"] == 20.0
    assert macros["calcium"] == 400.0
    assert macros["iron"] == 10.0
    assert macros["potassium"] == 600.0
