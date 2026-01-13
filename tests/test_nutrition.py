import pytest
from unittest.mock import patch
from app import models

def get_auth_token(client):
    # Create user first
    client.post("/api/v1/users/", json={"name": "testuser", "password": "pw", "weight_kg": 70, "height_cm": 170})
    res = client.post("/auth/token", data={"username": "testuser", "password": "pw"})
    return res.json()["access_token"]

def test_search_by_barcode_feature(client, session):
    token = get_auth_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Prepare a fake product that the Service would return
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

    # Patch the service method in app.services
    # Note: app.routers.nutrition imports 'services' from 'app'.
    with patch("app.services.OpenFoodFactsService.get_product", return_value=fake_product) as mock_get:
        # Perform search with a numeric query (barcode)
        response = client.get("/api/v1/nutrition/search?query=987654321", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Expectation: The endpoint should identify it's a barcode, call the service, and return the result.
        # Current behavior (Failure): It searches DB by name "987654321", finds nothing, returns [].

        assert len(data) == 1, "Expected 1 result for barcode search"
        assert data[0]["food_name"] == "Mocked Product"
        assert data[0]["barcode"] == "987654321"

        # Verify the service was called
        mock_get.assert_called_once()
