import pytest
from fastapi.testclient import TestClient

def get_auth_token(client: TestClient, username: str = "testuser_ex"):
    # Create user
    # Note: UserCreate schema expects 'name', 'password', 'weight_kg', 'height_cm'
    # The 'username' field in the schema is actually 'name'.
    # But in my previous code I sent 'username' and 'name'.
    # Let's check schemas.py again. UserBase has name. UserCreate has password.

    # In my previous attempt:
    # "username": username, -> This might be ignored or cause error if extra fields forbidden
    # "name": "Test User", -> This is the unique name?

    # Wait, in auth.py: user = db.query(models.User).filter(models.User.name == form_data.username).first()
    # So the 'username' in login form corresponds to 'name' in User model.

    # So when creating user:
    # name = username (the login identifier)
    # password = ...

    client.post("/api/v1/users/", json={
        "name": username,
        "password": "password123",
        "weight_kg": 100.0,
        "height_cm": 180.0
    })
    # Login
    response = client.post("/auth/token", data={"username": username, "password": "password123"})
    # Handle case where user already exists from a previous run within same session/module
    if response.status_code != 200:
         # Try login directly if register failed (e.g. 400 user exists)
         pass

    if response.status_code == 200:
        return response.json()["access_token"]

    # If login failed, maybe create failed?
    # Actually client fixture uses a fresh DB per module, so user shouldn't exist unless created in same file.
    assert response.status_code == 200
    return response.json()["access_token"]

def test_new_exercises_calories(client: TestClient):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Weight = 100kg
    # Formula: (MET * weight * 3.5 / 200) * duration
    # Factor = 100 * 3.5 / 200 = 1.75
    # Calories = MET * 1.75 * 60

    # 1. Snow Shoveling (MET 6.0) -> 630
    res = client.post("/api/v1/log/exercise", json={
        "activity_type": "snow shoveling",
        "duration_minutes": 60
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert abs(data["calories_burned"] - 630.0) < 1.0

    # 2. Gardening (MET 4.0) -> 420
    res = client.post("/api/v1/log/exercise", json={
        "activity_type": "gardening",
        "duration_minutes": 60
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert abs(data["calories_burned"] - 420.0) < 1.0

    # 3. Weight Lifting (MET 6.0) -> 630
    res = client.post("/api/v1/log/exercise", json={
        "activity_type": "weight lifting",
        "duration_minutes": 60
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert abs(data["calories_burned"] - 630.0) < 1.0

    # 4. Rowing Machine (MET 7.0) -> 735
    res = client.post("/api/v1/log/exercise", json={
        "activity_type": "rowing machine",
        "duration_minutes": 60
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert abs(data["calories_burned"] - 735.0) < 1.0
