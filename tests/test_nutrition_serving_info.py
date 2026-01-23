import pytest
from app import models, schemas
import time

def get_auth_token(client):
    try:
        client.post("/api/v1/users/", json={"name": "testuser_wv", "password": "pw", "weight_kg": 70, "height_cm": 170})
    except:
        pass
    res = client.post("/auth/token", data={"username": "testuser_wv", "password": "pw"})
    if res.status_code != 200:
        res = client.post("/auth/token", data={"username": "testuser_wv", "password": "pw"})
    return res.json()["access_token"]

def test_create_food_with_weight_volume(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "food_name": "Dense Bar",
        "calories": 200,
        "protein": 10,
        "fat": 5,
        "carbs": 20,
        "serving_size_unit": "1 bar",
        "serving_weight_grams": 50.5,
        "serving_volume_ml": 40.2
    }

    res = client.post("/api/v1/nutrition/", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["food_name"] == "Dense Bar"
    assert data["serving_weight_grams"] == 50.5
    assert data["serving_volume_ml"] == 40.2

    # Verify DB
    obj = session.query(models.NutritionCache).filter_by(food_id=data["food_id"]).first()
    assert obj.serving_weight_grams == 50.5
    assert obj.serving_volume_ml == 40.2

def test_update_food_with_weight_volume(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create basic
    f = models.NutritionCache(food_name="Light Air", calories=0, source="MANUAL")
    session.add(f)
    session.commit()
    fid = f.food_id

    # Update
    payload = {
        "serving_weight_grams": 0.1,
        "serving_volume_ml": 1000.0
    }
    res = client.put(f"/api/v1/nutrition/{fid}", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["serving_weight_grams"] == 0.1
    assert data["serving_volume_ml"] == 1000.0

    session.expire_all()
    obj = session.query(models.NutritionCache).filter_by(food_id=fid).first()
    assert obj.serving_weight_grams == 0.1
    assert obj.serving_volume_ml == 1000.0

def test_v2_log_with_weight_volume(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # V2 Payload
    payload = {
        "quantity": 0, # Save only
        "variables": {
            "Variable1": {
                "metadata": {
                    "name": "Heavy Liquid",
                    "brand": "HeavyBrand"
                },
                "macros": {
                    "calories": 100,
                    "protein_g": 0,
                    "fat_g": 0,
                    "carbs_g": 0
                },
                "serving_info": {
                    "size": "1 cup",
                    "weight_g": 240.0,
                    "volume_ml": 236.6
                }
            }
        }
    }

    res = client.post("/api/v2/nutrition/log", json=payload, headers=headers)
    assert res.status_code == 200

    # Verify DB
    obj = session.query(models.NutritionCache).filter_by(food_name="Heavy Liquid").first()
    assert obj is not None
    assert obj.serving_weight_grams == 240.0
    assert obj.serving_volume_ml == 236.6

def test_v2_lookup_returns_weight_volume(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Setup DB
    f = models.NutritionCache(
        food_name="Mapped Food",
        barcode="999999",
        calories=100,
        serving_weight_grams=123.4,
        serving_volume_ml=567.8,
        source="MANUAL"
    )
    session.add(f)
    session.commit()

    res = client.get("/api/v2/nutrition/lookup/999999", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["serving_info"]["weight_g"] == 123.4
    assert data["serving_info"]["volume_ml"] == 567.8
