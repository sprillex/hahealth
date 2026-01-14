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
        sodium=10.0,
        source="OFF",
        is_user_visible=True
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
        protein=0.0,
        fat=0.0,
        carbs=0.0,
        fiber=0.0,
        sodium=0.0,
        source="OFF",
        is_user_visible=True
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
            "fiber": 5.0,
            "sodium": 150.0
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
    assert cache.sodium == 150.0
    # Default (missing save_food) should be Hidden (False)
    assert cache.is_user_visible == False

def test_webhook_food_log_missing_sodium(client, session):
    # Verify backward compatibility (no sodium in payload)
    token = get_auth_token(client)
    # create dedicated user/key
    user = models.User(name="no_sodium_user", weight_kg=70, height_cm=170, password_hash="pw")
    session.add(user)
    session.commit()
    raw_key = "no_sodium_key"
    api_key = models.APIKey(user_id=user.user_id, name="K", hashed_key=auth.hash_api_key(raw_key), is_active=True)
    session.add(api_key)
    session.commit()
    headers = {"X-Webhook-Secret": raw_key}

    payload = {
        "data_type": "FOOD_LOG",
        "payload": {
            "food_name": "No Sodium Food",
            "quantity": 1.0,
            "serving_size": 1.0,
            "meal_id": "Snack",
            "calories": 100.0
            # sodium missing
        }
    }
    res = client.post("/api/webhook/health", json=payload, headers=headers)
    assert res.status_code == 200

    cache = session.query(models.NutritionCache).filter(models.NutritionCache.food_name == "No Sodium Food").first()
    assert cache is not None
    assert cache.sodium == 0.0

def test_webhook_food_log_manual_macros_saved(client, session):
    token = get_auth_token(client)
    # We use webhook key though
    # Create User/Key again? Or reuse logic?
    # Simpler to create new
    user = models.User(name="save_test_user", weight_kg=70, height_cm=170, password_hash="pw")
    session.add(user)
    session.commit()
    raw_key = "save_test_key"
    api_key = models.APIKey(user_id=user.user_id, name="K", hashed_key=auth.hash_api_key(raw_key), is_active=True)
    session.add(api_key)
    session.commit()
    headers = {"X-Webhook-Secret": raw_key}

    food_name = "Saved Food"
    payload = {
        "data_type": "FOOD_LOG",
        "payload": {
            "food_name": food_name,
            "quantity": 1.0,
            "serving_size": 1.0,
            "meal_id": "Lunch",
            "calories": 100.0,
            "save_food": 1
        }
    }
    client.post("/api/webhook/health", json=payload, headers=headers)
    cache = session.query(models.NutritionCache).filter(models.NutritionCache.food_name == food_name).first()
    assert cache is not None
    assert cache.is_user_visible == True

def test_search_hides_invisible_foods(client, session):
    # Create visible and invisible foods
    visible = models.NutritionCache(
        food_name="Visible Apple", calories=50.0, protein=0.0, fat=0.0, carbs=0.0, fiber=0.0,
        is_user_visible=True, source="MANUAL"
    )
    hidden = models.NutritionCache(
        food_name="Hidden Apple", calories=50.0, protein=0.0, fat=0.0, carbs=0.0, fiber=0.0,
        is_user_visible=False, source="MANUAL"
    )
    session.add(visible)
    session.add(hidden)
    session.commit()

    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/nutrition/search?query=Apple", headers=headers)
    results = response.json()
    names = [r["food_name"] for r in results]
    assert "Visible Apple" in names
    assert "Hidden Apple" not in names

def test_manage_food_library(client, session):
    # Setup user
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a food
    f = models.NutritionCache(food_name="UpdateMe", calories=100.0, is_user_visible=True, source="MANUAL")
    session.add(f)
    session.commit()
    fid = f.food_id

    # 2. Get List
    res = client.get("/api/v1/nutrition/list", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 3. Get Detail
    res = client.get(f"/api/v1/nutrition/{fid}", headers=headers)
    assert res.status_code == 200
    assert res.json()["food_name"] == "UpdateMe"

    # 4. Update
    payload = {
        "food_name": "UpdatedName",
        "calories": 200.0,
        "is_user_visible": False
    }
    res = client.put(f"/api/v1/nutrition/{fid}", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["food_name"] == "UpdatedName"
    assert res.json()["is_user_visible"] == False

    # 5. Verify persistence
    session.expire_all()
    db_obj = session.query(models.NutritionCache).filter(models.NutritionCache.food_id == fid).first()
    assert db_obj.food_name == "UpdatedName"
    assert db_obj.calories == 200.0
    assert db_obj.is_user_visible == False

    # 6. Verify List Filter (hidden should be excluded by default)
    res = client.get("/api/v1/nutrition/list", headers=headers)
    names = [x["food_name"] for x in res.json()]
    assert "UpdatedName" not in names

    # 7. Verify List Filter (include_hidden=True)
    res = client.get("/api/v1/nutrition/list?include_hidden=true", headers=headers)
    names = [x["food_name"] for x in res.json()]
    assert "UpdatedName" in names

def test_delete_food_logic(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create unused food
    unused = models.NutritionCache(food_name="DeleteMe", calories=10, is_user_visible=True, source="MANUAL")
    session.add(unused)
    session.commit()
    uid = unused.food_id

    # 2. Delete unused -> Should succeed
    res = client.delete(f"/api/v1/nutrition/{uid}", headers=headers)
    assert res.status_code == 200
    assert session.query(models.NutritionCache).filter_by(food_id=uid).first() is None

    # 3. Create used food
    used = models.NutritionCache(food_name="KeepMe", calories=10, is_user_visible=True, source="MANUAL")
    session.add(used)
    session.commit()
    # Log it (creates dependency)
    # We need a user ID. auth helper ensures user exists.
    # We need to get the user ID from the token or just assume 1 if fresh db.
    # Let's fetch /users/me to be safe.
    me = client.get("/api/v1/users/me", headers=headers).json()
    user_id = me["user_id"]

    log = models.FoodItemLog(user_id=user_id, food_id=used.food_id, meal_id="Snack", serving_size=1, quantity=1)
    session.add(log)
    session.commit()

    # 4. Delete used -> Should fail 400
    res = client.delete(f"/api/v1/nutrition/{used.food_id}", headers=headers)
    assert res.status_code == 400
    assert "Cannot delete" in res.json()["detail"]

def test_list_search_filter(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    f1 = models.NutritionCache(food_name="Apple Pie", calories=1, is_user_visible=True, source="MANUAL")
    f2 = models.NutritionCache(food_name="Banana Bread", calories=1, is_user_visible=True, source="MANUAL")
    session.add_all([f1, f2])
    session.commit()

    # Search "Apple"
    res = client.get("/api/v1/nutrition/list?search=Apple", headers=headers)
    data = res.json()
    names = [x["food_name"] for x in data]
    assert "Apple Pie" in names
    assert "Banana Bread" not in names

from app.services import OpenFoodFactsService

def test_sodium_unit_conversion(session):
    # Mock Response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": 1,
        "product": {
            "product_name": "Test Sodium Product",
            "nutriments": {
                "energy-kcal_100g": 100,
                "proteins_100g": 10,
                "fat_100g": 5,
                "carbohydrates_100g": 20,
                "fiber_100g": 2,
                "sodium_100g": 0.5 # 0.5 grams
            }
        }
    }

    with patch("requests.get", return_value=mock_response):
        service = OpenFoodFactsService()
        barcode = "123456789"
        product = service.get_product(barcode, session)

        assert product is not None
        assert product.food_name == "Test Sodium Product"
        # 0.5 grams * 1000 = 500 mg
        assert product.sodium == 500.0
