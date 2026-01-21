import pytest
from unittest.mock import patch
from app import models, auth

def get_auth_headers(session):
    # 1. Ensure User
    user = session.query(models.User).filter_by(name="v2_test_user").first()
    if not user:
        user = models.User(
            name="v2_test_user",
            password_hash="mock_hash", # We won't use password login
            weight_kg=70,
            height_cm=170
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # 2. Create API Key
    raw_key = "test_api_key_v2"
    hashed = auth.hash_api_key(raw_key)

    existing_key = session.query(models.APIKey).filter_by(hashed_key=hashed).first()
    if not existing_key:
        api_key = models.APIKey(
            user_id=user.user_id,
            name="Test Key V2",
            hashed_key=hashed,
            is_active=True
        )
        session.add(api_key)
        session.commit()

    return {"Authorization": f"Bearer {raw_key}"}

def test_v2_lookup_existing_food(client, session):
    headers = get_auth_headers(session)

    # 1. Create a food in DB
    food = models.NutritionCache(
        barcode="111111111111",
        food_name="Existing Apple",
        calories=100.0,
        protein=1.0,
        fat=2.0,
        carbs=20.0,
        fiber=3.0,
        sodium=5.0,
        brand="Nature",
        serving_size_unit="1 apple",
        is_user_visible=True,
        source="MANUAL"
    )
    # Check if exists to avoid dup
    if not session.query(models.NutritionCache).filter_by(barcode="111111111111").first():
        session.add(food)
        session.commit()

    # 2. Lookup via V2
    response = client.get(f"/api/v2/nutrition/lookup/111111111111", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["metadata"]["name"] == "Existing Apple"
    assert data["metadata"]["upc"] == "111111111111"
    assert data["macros"]["calories"] == 100.0
    assert data["macros"]["fiber_g"] == 3.0

    # DB check - count shouldn't change
    assert session.query(models.NutritionCache).filter_by(barcode="111111111111").count() == 1

def test_v2_lookup_remote_new_food(client, session):
    headers = get_auth_headers(session)

    # 1. Mock remote service
    fake_product = models.NutritionCache(
        barcode="222222222222",
        food_name="Remote Cookie",
        calories=200.0,
        protein=2.0,
        fat=10.0,
        carbs=30.0,
        fiber=1.0,
        sodium=50.0,
        brand="CookieCo",
        serving_size_unit="1 cookie",
        source="MANUAL",
        is_user_visible=True
    )

    with patch("app.services.CustomNutritionService._fetch_remote_product", return_value=fake_product) as mock_fetch:
        # 2. Lookup via V2
        response = client.get("/api/v2/nutrition/lookup/222222222222", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["name"] == "Remote Cookie"
        assert data["metadata"]["upc"] == "222222222222"
        assert data["macros"]["calories"] == 200.0

        mock_fetch.assert_called_once_with("222222222222")

        # 3. VERIFY NOT SAVED to DB
        assert session.query(models.NutritionCache).filter_by(barcode="222222222222").count() == 0

def test_v2_lookup_not_found(client, session):
    headers = get_auth_headers(session)

    with patch("app.services.CustomNutritionService._fetch_remote_product", return_value=None):
        response = client.get("/api/v2/nutrition/lookup/999999999999", headers=headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Food not found"
