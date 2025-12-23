from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
import pytest
from app import models, auth

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    # Setup
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    yield client
    # Teardown
    Base.metadata.drop_all(bind=engine)
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")

def test_create_user(client):
    response = client.post(
        "/api/v1/users/",
        json={"name": "testuser", "password": "testpassword", "weight_kg": 70, "height_cm": 175},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "testuser"
    assert "user_id" in data

def test_login(client):
    response = client.post(
        "/auth/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    return data["access_token"]

def test_create_medication(client):
    token = test_login(client)
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

def test_webhook_bp(client):
    # 1. Create API Key for user
    # Need to access DB directly for this setup
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.name == "testuser").first()
    raw_key = "test_webhook_key"
    hashed_key = auth.hash_api_key(raw_key)
    new_key = models.APIKey(user_id=user.user_id, name="Test Key", hashed_key=hashed_key)
    db.add(new_key)
    db.commit()
    db.close()

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

def test_webhook_get_nutrition(client):
    # Setup - insert cache item and ensure API key
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.name == "testuser").first()

    # Create a unique key for this test
    raw_key = "test_webhook_key_nutrition"
    hashed_key = auth.hash_api_key(raw_key)
    # Check if key exists (it shouldn't in a clean test db run, but in interactive dev it might)
    # Since client fixture has module scope, we rely on unique key name.
    new_key = models.APIKey(user_id=user.user_id, name="Test Key Nutrition", hashed_key=hashed_key)
    db.add(new_key)

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
    db.add(cache_item)
    db.commit()
    db.close()

    response = client.get(
        "/api/webhook/nutrition/123456",
        headers={"X-Webhook-Secret": raw_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["food_name"] == "Test Food"
    assert data["calories"] == 100.0
    assert data["source"] == "TEST"

    # Test Not Found
    # We need to ensure it returns 404. Since we might have internet access,
    # we should pick a barcode that definitely doesn't exist or mock the service.
    # However, mocking inside TestClient flow is tricky because it runs in the same process but
    # we need to patch the module used by the app.

    # Let's try to patch requests.get in app.services
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
             # Should be handled by cache, but just in case
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
