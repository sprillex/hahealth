import pytest
from app import models, schemas
from datetime import datetime, timezone

def get_auth_token(client):
    try:
        client.post("/api/v1/users/", json={"name": "testuser_v2", "password": "pw", "weight_kg": 70, "height_cm": 170})
    except:
        pass
    res = client.post("/auth/token", data={"username": "testuser_v2", "password": "pw"})
    if res.status_code != 200:
        res = client.post("/auth/token", data={"username": "testuser_v2", "password": "pw"})
    return res.json()["access_token"]

def test_log_v2_new_food(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
      "quantity": 2.0,
      "timestamp": "2024-05-21T10:00:00Z",
      "meal": "Breakfast",
      "variables": {
        "New V2 Food": {
          "metadata": {
            "name": "New V2 Food",
            "brand": "BrandX",
            "upc": "99990000",
            "srv_per_cont": 2.5
          },
          "macros": {
            "calories": 200.0,
            "fat_g": 10.0,
            "cholesterol_mg": 5.0,
            "sodium_mg": 50.0,
            "carbs_g": 20.0,
            "fiber_g": 3.0,
            "total_sugars_g": 10.0,
            "added_sugars_g": 5.0,
            "protein_g": 5.0
          },
          "micros": {
            "vit_d_mcg": 10.0,
            "calcium_mg": 100.0,
            "iron_mg": 2.0,
            "potassium_mg": 200.0
          },
          "serving_info": {
            "size": "1 bar"
          },
          "analysis": {
            "score_color": "green",
            "health_insight": "Good",
            "pairing_tip": "Eat with water"
          }
        }
      }
    }

    res = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["food_name"] == "New V2 Food"
    assert data["quantity"] == 2.0
    assert data["log_id"] is not None

    # Verify Cache
    food = session.query(models.NutritionCache).filter(models.NutritionCache.barcode == "99990000").first()
    assert food is not None
    assert food.brand == "BrandX"
    assert food.calories == 200.0
    assert food.cholesterol == 5.0
    assert food.total_sugars == 10.0
    assert food.serving_size_unit == "1 bar"
    assert food.health_score == "green"

    # Verify Log
    log = session.query(models.FoodItemLog).filter(models.FoodItemLog.food_id == food.food_id).first()
    assert log is not None
    assert log.quantity == 2.0

def test_log_v2_update_food(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create existing
    f = models.NutritionCache(food_name="Update Me", barcode="8888", calories=100.0, brand="OldBrand")
    session.add(f)
    session.commit()

    payload = {
      "quantity": 1.0,
      "variables": {
        "Update Me": {
            "metadata": {
                "name": "Update Me",
                "brand": "NewBrand",
                "upc": "8888"
            },
            "macros": {
                "calories": 150.0,
                "fat_g": 0, "carbs_g": 0, "protein_g": 0
            },
            "serving_info": {"size": "1 pack"}
        }
      }
    }

    res = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert res.status_code == 200

    session.refresh(f)
    assert f.brand == "NewBrand"
    assert f.calories == 150.0
    assert f.serving_size_unit == "1 pack"

def test_v1_edit_library_with_new_fields(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    f = models.NutritionCache(food_name="Edit V1", calories=100.0, source="MANUAL")
    session.add(f)
    session.commit()

    payload = {
        "calories": 120.0,
        "brand": "EditedBrand",
        "cholesterol": 15.0
    }

    res = client.put(f"/api/v1/nutrition/{f.food_id}", json=payload, headers=headers)
    assert res.status_code == 200

    session.refresh(f)
    assert f.calories == 120.0
    assert f.brand == "EditedBrand"
    assert f.cholesterol == 15.0

def test_log_v2_save_only(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
      "quantity": 0.0, # Should trigger Save Only
      "variables": {
        "Saved Only Food": {
          "metadata": {
            "name": "Saved Only Food",
            "brand": "SaveBrand"
          },
          "macros": {
            "calories": 100.0, "fat_g": 0, "carbs_g": 0, "protein_g": 0
          }
        }
      }
    }

    res = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["log_id"] is None
    assert data["quantity"] == 0.0

    # Verify Food Created
    f = session.query(models.NutritionCache).filter(models.NutritionCache.food_name == "Saved Only Food").first()
    assert f is not None
    assert f.brand == "SaveBrand"

    # Verify NO Log
    logs = session.query(models.FoodItemLog).filter(models.FoodItemLog.food_id == f.food_id).all()
    assert len(logs) == 0

def test_generate_upc_endpoint(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v2/nutrition/generate_upc", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "upc" in data
    upc = data["upc"]
    assert len(upc) == 12
    assert upc.startswith("4")

    # Call again to ensure consistent behavior
    res2 = client.get("/api/v2/nutrition/generate_upc", headers=headers)
    assert res2.status_code == 200
    upc2 = res2.json()["upc"]
    assert len(upc2) == 12
    assert upc2.startswith("4")
