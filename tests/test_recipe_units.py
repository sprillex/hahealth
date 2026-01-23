import pytest
from app import models, auth

def get_auth_token(client, session):
    # Create user if not exists
    user = session.query(models.User).filter_by(name="TestRecipeUser").first()
    if not user:
        user = models.User(name="TestRecipeUser", weight_kg=70, height_cm=170)
        # We need a password hash.
        # But we can also override auth for this test module or function?
        # Creating a user and logging in is cleaner integration test.
        # But hashing password is slow.
        # Let's use dependency override for auth within the test function context.
        pass
    return "token"

# Helper to override auth
@pytest.fixture
def auth_override(client):
    from app.main import app
    def override():
        return models.User(user_id=1, name="TestRecipeUser", is_admin=True)

    app.dependency_overrides[auth.get_current_user] = override
    yield
    app.dependency_overrides.pop(auth.get_current_user, None)

@pytest.fixture
def db_data(session):
    # Create User
    if not session.query(models.User).filter_by(user_id=1).first():
        user = models.User(user_id=1, name="TestRecipeUser")
        session.add(user)
        session.commit()

def test_recipe_unit_persistence_and_calc(client, session, auth_override, db_data):
    # Create ingredient with known volume
    ing = models.NutritionCache(
        food_name="Milk",
        calories=100,
        protein=10,
        serving_volume_ml=236.588,
        source="MANUAL",
        is_user_visible=True
    )
    session.add(ing)
    session.commit()
    ing_id = ing.food_id

    # Create Recipe with 0.5 cup
    payload = {
        "name": "Half Cup Milk",
        "total_servings": 1.0,
        "ingredients": [
            {
                "food_id": ing_id,
                "quantity": 0.5,
                "unit": "cup"
            }
        ]
    }

    response = client.post("/api/v1/recipes/", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Check persistence
    assert data["ingredients"][0]["unit"] == "cup"
    assert data["ingredients"][0]["quantity"] == 0.5

    # Check Calculation
    # 50 cals
    assert abs(data["current_food"]["calories"] - 50.0) < 0.1

def test_recipe_unit_default_fallback(client, session, auth_override, db_data):
    ing = models.NutritionCache(food_name="Bread", calories=100, source="MANUAL")
    session.add(ing)
    session.commit()
    ing_id = ing.food_id

    payload = {
        "name": "Toast",
        "total_servings": 1.0,
        "ingredients": [
            {"food_id": ing_id, "quantity": 2.0}
        ]
    }

    response = client.post("/api/v1/recipes/", json=payload)
    data = response.json()

    assert data["ingredients"][0]["unit"] == "serving"
    assert data["current_food"]["calories"] == 200.0

def test_update_recipe_unit(client, session, auth_override, db_data):
    # Ingredient: 100 cal per 100ml
    ing = models.NutritionCache(food_name="Liquid", calories=100, serving_volume_ml=100.0, source="MANUAL")
    session.add(ing)
    session.commit()
    ing_id = ing.food_id

    # Create with 100ml (1 serving)
    payload = {
        "name": "Drink",
        "total_servings": 1.0,
        "ingredients": [{"food_id": ing_id, "quantity": 100.0, "unit": "ml"}]
    }
    create_res = client.post("/api/v1/recipes/", json=payload)
    recipe_id = create_res.json()["recipe_id"]

    assert abs(create_res.json()["current_food"]["calories"] - 100.0) < 0.1

    # Update to 1 cup (236.588 ml)
    update_payload = {
        "total_servings": 1.0,
        "ingredients": [{"food_id": ing_id, "quantity": 1.0, "unit": "cup"}]
    }

    update_res = client.put(f"/api/v1/recipes/{recipe_id}", json=update_payload)
    assert update_res.status_code == 200
    data = update_res.json()

    assert data["ingredients"][0]["unit"] == "cup"
    assert abs(data["current_food"]["calories"] - 236.6) < 0.5
