from app import models, auth
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

def test_update_meal_settings(client: TestClient, session: Session):
    # Create user
    user = models.User(
        name="testuser_meals",
        password_hash=auth.get_password_hash("password"),
        weight_kg=70.0,
        height_cm=175.0
    )
    session.add(user)
    session.commit()

    # Login
    response = client.post("/auth/token", data={"username": "testuser_meals", "password": "password"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update settings
    payload = {
        "meal_breakfast_start": "06:00:00",
        "meal_lunch_start": "12:00:00",
        "meal_dinner_start": "18:00:00",
        "meal_dinner_end": "20:00:00"
    }

    response = client.put("/api/v1/users/me", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["meal_breakfast_start"] == "06:00:00"
    assert data["meal_lunch_start"] == "12:00:00"
    assert data["meal_dinner_start"] == "18:00:00"
    assert data["meal_dinner_end"] == "20:00:00"

    # Verify persistence
    response = client.get("/api/v1/users/me", headers=headers)
    data = response.json()
    assert data["meal_breakfast_start"] == "06:00:00"
