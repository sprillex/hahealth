from app.database import Base
from app import models, auth
import pytest

def test_create_user(client):
    response = client.post(
        "/api/v1/users/",
        json={"name": "testuser", "password": "testpassword", "weight_kg": 70, "height_cm": 175},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "testuser"
    assert "user_id" in data

def get_auth_token(client):
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def test_login(client):
    token = get_auth_token(client)
    assert token is not None

def test_create_medication(client):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/medications/",
        json={
            "name": "Ibuprofen",
            "frequency": "Daily",
            "type": "OTC",
            "current_inventory": 20,
            "refills_remaining": 5
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ibuprofen"

def test_webhook_bp(client, session):
    # 1. Create API Key for user using the session fixture
    user = session.query(models.User).filter(models.User.name == "testuser").first()
    # Ensure user exists (might depend on previous test order if using shared DB)
    if not user:
        pytest.skip("User testuser not found, skipping webhook test")

    raw_key = "test_webhook_key"
    hashed_key = auth.hash_api_key(raw_key)
    new_key = models.APIKey(user_id=user.user_id, name="Test Key", hashed_key=hashed_key)
    session.add(new_key)
    session.commit()

    response = client.post(
        "/api/webhook/health",
        json={
            "data_type": "BLOOD_PRESSURE",
            "payload": {
                "systolic": 120,
                "diastolic": 80,
                "pulse": 70,
                "location": "Left Arm",
                "stress_level": 3,
                "meds_taken_before": "NO"
            }
        },
        headers={"X-Webhook-Secret": raw_key}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_webhook_invalid_key(client):
    response = client.post(
        "/api/webhook/health",
        json={
            "data_type": "BLOOD_PRESSURE",
            "payload": {}
        },
        headers={"X-Webhook-Secret": "wrong_key"}
    )
    assert response.status_code == 401

def test_webhook_get_nutrition(client, session):
    # Setup - insert cache item and ensure API key
    user = session.query(models.User).filter(models.User.name == "testuser").first()
    if not user:
        pytest.skip("User testuser not found")

    # Create a unique key for this test
    raw_key = "test_webhook_key_nutrition"
    hashed_key = auth.hash_api_key(raw_key)
    new_key = models.APIKey(user_id=user.user_id, name="Test Key Nutrition", hashed_key=hashed_key)
    session.add(new_key)

    # Add nutrition item manually to DB to avoid external API call in test
    cache_item = models.NutritionCache(
        barcode="123456",
        food_name="Test Food",
        calories=100.0,
        protein=10.0,
        fat=5.0,
        carbs=20.0,
        fiber=2.0,
        source="TEST"
    )
    session.add(cache_item)
    session.commit()

    response = client.get(
        "/api/webhook/nutrition/123456",
        headers={"X-Webhook-Secret": raw_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["food_name"] == "Test Food"
    assert data["calories"] == 100.0
    assert data["source"] == "TEST"

    # Test Not Found with Mock
    import app.services
    original_get = app.services.requests.get

    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json

    def mock_get(url):
        if "123456" in url:
             return MockResponse(200, {"status": 1, "product": {"product_name": "Test Food"}})
        return MockResponse(404, {})

    app.services.requests.get = mock_get

    try:
        response_nf = client.get(
            "/api/webhook/nutrition/99999999",
            headers={"X-Webhook-Secret": raw_key}
        )
        assert response_nf.status_code == 404
    finally:
        app.services.requests.get = original_get
