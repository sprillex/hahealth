import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app import models, auth
import hashlib

# Setup In-Memory DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create Tables
Base.metadata.create_all(bind=engine)

# Create User and API Key
db = TestingSessionLocal()
user = models.User(name="apikey_user", password_hash="hash", weight_kg=70, height_cm=170)
db.add(user)
db.commit()
db.refresh(user)

raw_key = "my_secret_api_key_123"
hashed = auth.hash_api_key(raw_key)
api_key = models.APIKey(user_id=user.user_id, name="Test Key", hashed_key=hashed, is_active=True)
db.add(api_key)
db.commit()
db.close()

client = TestClient(app)

def repro_apikey_auth():
    print("Testing API Key in Bearer Header...")

    # Payload
    payload = {
        "food_name": "API Key Food",
        "serving_size": 1,
        "quantity": 1,
        "calories": 100,
        "meal_id": "Snack"
    }

    # 1. Test with Correct API Key
    headers = {"Authorization": f"Bearer {raw_key}"}
    resp = client.post("/api/v1/nutrition/log", json=payload, headers=headers)
    print(f"Response Code: {resp.status_code}")
    print(f"Response Body: {resp.json()}")

    if resp.status_code == 200:
        print("SUCCESS: API Key accepted as Bearer token.")
    else:
        print("FAILURE: API Key rejected.")

    # 2. Test with Invalid Key
    headers_invalid = {"Authorization": "Bearer wrong_key"}
    resp_inv = client.post("/api/v1/nutrition/log", json=payload, headers=headers_invalid)
    print(f"Invalid Key Code: {resp_inv.status_code}")

if __name__ == "__main__":
    repro_apikey_auth()
