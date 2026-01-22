import pytest
from app import models, auth
from unittest.mock import patch

def get_auth_token(client):
    try:
        client.post("/api/v1/users/", json={"name": "testuser_import", "password": "pw", "weight_kg": 70, "height_cm": 170})
    except:
        pass
    res = client.post("/auth/token", data={"username": "testuser_import", "password": "pw"})
    if res.status_code != 200:
        res = client.post("/auth/token", data={"username": "testuser_import", "password": "pw"})
    return res.json()["access_token"]

def test_check_existence_new_food(client, session):
    """Test check_existence=True for a food that does NOT exist (should be 200 OK)"""
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "quantity": 0.0,
        "variables": {
            "NewFood": {
                "metadata": {"name": "New Check Food", "upc": "999999001"},
                "macros": {"calories": 100, "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fat_g": 0}
            }
        }
    }

    response = client.post("/api/v2/nutrition/log?check_existence=true", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["detail"] == "Food available"

    # Verify NOT created
    existing = session.query(models.NutritionCache).filter_by(barcode="999999001").first()
    assert existing is None


def test_check_existence_existing_food(client, session):
    """Test check_existence=True for a food that DOES exist (should be 409 Conflict)"""
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Pre-create food
    food = models.NutritionCache(
        food_name="Existing Check Food",
        barcode="999999002",
        calories=100.0,
        protein=0, fat=0, carbs=0, fiber=0, sodium=0,
        source="MANUAL",
        is_user_visible=True
    )
    session.add(food)
    session.commit()

    payload = {
        "quantity": 0.0,
        "variables": {
            "ExistingFood": {
                "metadata": {"name": "Existing Check Food", "upc": "999999002"},
                "macros": {"calories": 100, "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fat_g": 0}
            }
        }
    }

    response = client.post("/api/v2/nutrition/log?check_existence=true", json=payload, headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "Food already exists"
    assert response.json()["food_name"] == "Existing Check Food"

def test_check_existence_create_flow(client, session):
    """Test normal creation (check_existence=False)"""
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "quantity": 0.0,
        "variables": {
            "CreateFood": {
                "metadata": {"name": "Create Flow Food", "upc": "999999003"},
                "macros": {"calories": 150, "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fat_g": 0}
            }
        }
    }

    # Normal request
    response = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert response.status_code == 200

    # Verify created
    existing = session.query(models.NutritionCache).filter_by(barcode="999999003").first()
    assert existing is not None
    assert existing.calories == 150.0

def test_check_existence_update_flow(client, session):
    """Test normal update (check_existence=False)"""
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Pre-create food
    food = models.NutritionCache(
        food_name="Update Flow Food",
        barcode="999999004",
        calories=100.0,
        protein=0, fat=0, carbs=0, fiber=0, sodium=0,
        source="MANUAL",
        is_user_visible=True
    )
    session.add(food)
    session.commit()

    payload = {
        "quantity": 0.0,
        "variables": {
            "UpdateFood": {
                "metadata": {"name": "Update Flow Food", "upc": "999999004"},
                "macros": {"calories": 200, "protein_g": 0, "fat_g": 0, "carbs_g": 0, "fat_g": 0}
            }
        }
    }

    # Normal request (Upsert)
    response = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert response.status_code == 200

    # Verify updated
    session.refresh(food)
    assert food.calories == 200.0
