import pytest
from unittest.mock import patch
from app import models, auth, services

def get_auth_headers(session):
    # 1. Ensure User
    user = session.query(models.User).filter_by(name="fuzzy_test_user").first()
    if not user:
        user = models.User(
            name="fuzzy_test_user",
            password_hash="mock_hash",
            weight_kg=70,
            height_cm=170
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # 2. Create API Key
    raw_key = "test_api_key_fuzzy"
    hashed = auth.hash_api_key(raw_key)

    existing_key = session.query(models.APIKey).filter_by(hashed_key=hashed).first()
    if not existing_key:
        api_key = models.APIKey(
            user_id=user.user_id,
            name="Test Key Fuzzy",
            hashed_key=hashed,
            is_active=True
        )
        session.add(api_key)
        session.commit()

    return {"Authorization": f"Bearer {raw_key}"}

def test_lookup_fuzzy_stripping_zeros(client, session):
    """
    DB has '00123'. User looks up '123'. Should find '00123'.
    """
    headers = get_auth_headers(session)

    # 1. Create a food in DB with leading zeros
    food = models.NutritionCache(
        barcode="00123",
        food_name="Fuzzy Item 00123",
        calories=123.0,
        source="MANUAL",
        is_user_visible=True
    )
    if not session.query(models.NutritionCache).filter_by(barcode="00123").first():
        session.add(food)
        session.commit()

    # 2. Lookup via V2 using stripped barcode
    # Mock remote to ensure it's hitting local cache
    with patch("app.services.CustomNutritionService._fetch_remote_product", return_value=None):
        response = client.get("/api/v2/nutrition/lookup/123", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["name"] == "Fuzzy Item 00123"
        assert data["metadata"]["upc"] == "00123" # Returns the DB barcode
        assert data["macros"]["calories"] == 123.0

def test_lookup_fuzzy_adding_zeros(client, session):
    """
    DB has '456'. User looks up '00456'. Should find '456'.
    """
    headers = get_auth_headers(session)

    # 1. Create a food in DB without leading zeros
    food = models.NutritionCache(
        barcode="456",
        food_name="Fuzzy Item 456",
        calories=456.0,
        source="MANUAL",
        is_user_visible=True
    )
    if not session.query(models.NutritionCache).filter_by(barcode="456").first():
        session.add(food)
        session.commit()

    # 2. Lookup via V2 using padded barcode
    with patch("app.services.CustomNutritionService._fetch_remote_product", return_value=None):
        response = client.get("/api/v2/nutrition/lookup/00456", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["metadata"]["name"] == "Fuzzy Item 456"
        assert data["metadata"]["upc"] == "456" # Returns the DB barcode

def test_lookup_exact_match_priority(client, session):
    """
    DB has '789' and '00789'. User looks up '789'. Should find '789'.
    """
    headers = get_auth_headers(session)

    # Create both
    f1 = models.NutritionCache(barcode="789", food_name="Item 789", calories=100.0, source="MANUAL", is_user_visible=True)
    f2 = models.NutritionCache(barcode="00789", food_name="Item 00789", calories=100.0, source="MANUAL", is_user_visible=True)

    for f in [f1, f2]:
        if not session.query(models.NutritionCache).filter_by(barcode=f.barcode).first():
            session.add(f)
    session.commit()

    with patch("app.services.CustomNutritionService._fetch_remote_product", return_value=None):
        response = client.get("/api/v2/nutrition/lookup/789", headers=headers)
        assert response.status_code == 200
        assert response.json()["metadata"]["name"] == "Item 789" # Exact match

        response = client.get("/api/v2/nutrition/lookup/00789", headers=headers)
        assert response.status_code == 200
        assert response.json()["metadata"]["name"] == "Item 00789" # Exact match
