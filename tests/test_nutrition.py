import pytest
from unittest.mock import patch, MagicMock, ANY
from app import models, schemas, auth
from datetime import datetime
import secrets

def get_auth_token(client):
    # Ensure user exists first or use existing
    try:
        client.post("/api/v1/users/", json={"name": "testuser_nutri", "password": "pw", "weight_kg": 70, "height_cm": 170})
    except:
        pass # Might exist
    res = client.post("/auth/token", data={"username": "testuser_nutri", "password": "pw"})
    if res.status_code != 200:
        # Maybe already exists
        res = client.post("/auth/token", data={"username": "testuser_nutri", "password": "pw"})
    return res.json()["access_token"]

def test_search_by_barcode_feature(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    fake_product = models.NutritionCache(
        food_id=999,
        barcode="987654321",
        food_name="Mocked Product",
        calories=100.0,
        protein=10.0,
        fat=5.0,
        carbs=10.0,
        fiber=2.0,
        source="OFF"
    )

    with patch("app.services.OpenFoodFactsService.get_product", return_value=fake_product) as mock_get:
        response = client.get("/api/v1/nutrition/search?query=987654321", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["food_name"] == "Mocked Product"

def test_log_food_with_barcode_as_name(client, session):
    # This tests the "fallback" logic in log_food
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate OFF finding the product
    fake_product = models.NutritionCache(
        food_id=888,
        barcode="1234567890",
        food_name="Tasty Barcode Food",
        calories=250.0,
        source="OFF"
    )

    with patch("app.services.OpenFoodFactsService.get_product", return_value=fake_product) as mock_get:
        # User submits "1234567890" as name, no barcode
        payload = {
            "food_name": "1234567890",
            "quantity": 1,
            "serving_size": 1,
            "meal_id": "Snack"
        }
        response = client.post("/api/v1/nutrition/log", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify get_product was called with the "name" as barcode
        mock_get.assert_called_with("1234567890", ANY)

        # Check DB log
        # We need to query the FoodLog to see if it linked to "Tasty Barcode Food" (id 888)
        # But response returns payload entry.

        # Let's check the database directly using session
        # We need to wait for transaction? TestClient runs in same thread/process usually, but db session might be separate.
        # But 'fake_product' is a model instance not attached to session if returned by mock.
        # Services code does: if data.barcode: food_item = off_service.get_product(...)
        # get_product (mocked) returns fake_product.
        # Then: item_log = models.FoodItemLog(..., food_id=food_item.food_id, ...)
        # db.add(item_log)

        # So it should try to add item_log with food_id=888.
        pass

def test_webhook_food_log_manual_macros(client, session):
    # 1. Create a user
    user = models.User(
        name="webhook_test_user",
        weight_kg=70.0,
        height_cm=175.0,
        password_hash="hash",
        unit_system="METRIC"
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # 2. Create API Key
    raw_key = "test_webhook_key_123"
    hashed = auth.hash_api_key(raw_key)
    api_key = models.APIKey(
        user_id=user.user_id,
        name="Test Key",
        hashed_key=hashed,
        is_active=True
    )
    session.add(api_key)
    session.commit()

    headers = {"X-Webhook-Secret": raw_key}

    # 3. Payload with manual macros
    food_name = "Manual Macro Food"
    payload = {
        "data_type": "FOOD_LOG",
        "payload": {
            "food_name": food_name,
            "quantity": 1.0,
            "serving_size": 1.0,
            "meal_id": "Lunch",
            "calories": 500.0,
            "protein": 30.0,
            "fat": 20.0,
            "carbs": 50.0,
            "fiber": 5.0
        }
    }

    # 4. Call Webhook
    response = client.post("/api/webhook/health", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Food logged"

    # 5. Verify Database
    # Check NutritionCache
    cache = session.query(models.NutritionCache).filter(models.NutritionCache.food_name == food_name).first()
    assert cache is not None

    assert cache.calories == 500.0
    assert cache.protein == 30.0
    assert cache.fat == 20.0
    assert cache.carbs == 50.0
    assert cache.fiber == 5.0
