from app import models, auth
from fastapi.testclient import TestClient

def test_api_key_auth_success(client: TestClient, session):
    # 1. Create User
    user = models.User(name="apikey_user", password_hash="hash")
    session.add(user)
    session.commit()
    session.refresh(user)

    # 2. Generate API Key
    raw_key = auth.generate_api_key()
    hashed_key = auth.hash_api_key(raw_key)
    api_key = models.APIKey(user_id=user.user_id, name="Test Key", hashed_key=hashed_key)
    session.add(api_key)
    session.commit()

    # 3. Try to log food using API Key as Bearer token
    headers = {"Authorization": f"Bearer {raw_key}"}
    payload = {
        "food_name": "Test Food",
        "calories": 100,
        "protein": 10,
        "fat": 5,
        "carbs": 5,
        "meal_id": "Breakfast",
        "serving_size": 1,
        "quantity": 1
    }

    response = client.post("/api/v1/nutrition/log", json=payload, headers=headers)

    # 4. Assert Success
    assert response.status_code == 200
    data = response.json()
    assert data["food_name"] == "Test Food"
    assert data["calories"] == 100

    # 5. Verify log created in DB
    log = session.query(models.FoodItemLog).filter(models.FoodItemLog.user_id == user.user_id).first()
    assert log is not None
    assert log.nutrition_info.food_name == "Test Food"
