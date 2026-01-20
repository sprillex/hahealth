import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_db, Base
from app import models, auth
import datetime

# Setup Test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user():
    return models.User(user_id=1, name="TestUser", is_admin=True)

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[auth.get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create Dummy User
    user = models.User(user_id=1, name="TestUser", password_hash="hash", weight_kg=70, height_cm=170)
    db.add(user)

    # Create Ingredients
    ing1 = models.NutritionCache(food_name="Ingredient A", calories=100, protein=10, is_user_visible=True, source="MANUAL")
    ing2 = models.NutritionCache(food_name="Ingredient B", calories=50, fat=5, is_user_visible=True, source="MANUAL")
    db.add(ing1)
    db.add(ing2)
    db.commit()

    yield

    Base.metadata.drop_all(bind=engine)

def test_create_recipe():
    # Get ingredient IDs
    db = TestingSessionLocal()
    ing1 = db.query(models.NutritionCache).filter_by(food_name="Ingredient A").first()
    ing2 = db.query(models.NutritionCache).filter_by(food_name="Ingredient B").first()

    payload = {
        "name": "My Recipe",
        "total_servings": 2.0,
        "instructions": "Mix it.",
        "ingredients": [
            {"food_id": ing1.food_id, "quantity": 1.0}, # 100 cal
            {"food_id": ing2.food_id, "quantity": 2.0}  # 50*2 = 100 cal
        ]
    }

    response = client.post("/api/v1/recipes/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Recipe"
    assert len(data["ingredients"]) == 2

    # Check calculated nutrition
    # Total Cals = 100 + 100 = 200. Servings = 2. Per Serving = 100.
    assert data["current_food"]["calories"] == 100.0

    # Verify DB
    db.expire_all()
    recipe = db.query(models.Recipe).first()
    assert recipe.name == "My Recipe"
    assert recipe.current_food.source == "RECIPE"
    db.close()

def test_update_recipe_in_place():
    # Create first
    db = TestingSessionLocal()
    ing1 = db.query(models.NutritionCache).filter_by(food_name="Ingredient A").first()
    payload = {
        "name": "My Recipe",
        "total_servings": 1.0,
        "ingredients": [{"food_id": ing1.food_id, "quantity": 1.0}] # 100 cal
    }
    create_res = client.post("/api/v1/recipes/", json=payload)
    recipe_id = create_res.json()["recipe_id"]
    old_food_id = create_res.json()["current_food_id"]

    # Update (change quantity -> 2.0 -> 200 cal)
    update_payload = {
        "total_servings": 1.0,
        "ingredients": [{"food_id": ing1.food_id, "quantity": 2.0}]
    }
    response = client.put(f"/api/v1/recipes/{recipe_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["current_food"]["calories"] == 200.0
    assert data["current_food_id"] == old_food_id # Should be same (in place)
    db.close()

def test_update_recipe_history_preservation():
    db = TestingSessionLocal()
    ing1 = db.query(models.NutritionCache).filter_by(food_name="Ingredient A").first()

    # 1. Create Recipe
    payload = {"name": "Log Recipe", "total_servings": 1.0, "ingredients": [{"food_id": ing1.food_id, "quantity": 1.0}]}
    create_res = client.post("/api/v1/recipes/", json=payload)
    recipe_data = create_res.json()
    recipe_id = recipe_data["recipe_id"]
    original_food_id = recipe_data["current_food_id"]

    # 2. Log it
    log_payload = {
        "food_name": recipe_data["name"], # Name matching
        "quantity": 1.0,
        "serving_size": 1.0,
        "meal_id": "Lunch"
    }

    log_res = client.post("/api/v1/nutrition/log", json=log_payload)
    assert log_res.status_code == 200

    # Verify Log exists and points to original_food_id
    db.expire_all()
    log = db.query(models.FoodItemLog).first()
    assert log.food_id == original_food_id

    # 3. Update Recipe (Change Ingredients)
    update_payload = {
        "total_servings": 1.0,
        "ingredients": [{"food_id": ing1.food_id, "quantity": 2.0}] # 200 cals
    }
    update_res = client.put(f"/api/v1/recipes/{recipe_id}", json=update_payload)
    assert update_res.status_code == 200
    new_data = update_res.json()

    new_food_id = new_data["current_food_id"]
    assert new_food_id != original_food_id # Must be new ID

    # 4. Verify History
    db.expire_all()
    # Old log should still point to old ID
    log_check = db.query(models.FoodItemLog).first()
    assert log_check.food_id == original_food_id

    # Old food should be hidden
    old_food = db.query(models.NutritionCache).filter_by(food_id=original_food_id).first()
    assert old_food.is_user_visible == False

    # New food should be visible and have updated cals
    new_food = db.query(models.NutritionCache).filter_by(food_id=new_food_id).first()
    assert new_food.is_user_visible == True
    assert new_food.calories == 200.0

    db.close()

def test_search_scope():
    db = TestingSessionLocal()
    # Create a recipe manually since we need ID for ingredients, but lets use API
    # Need ingredient ID
    ing = db.query(models.NutritionCache).first()
    ing_id = ing.food_id
    db.close()

    client.post("/api/v1/recipes/", json={
        "name": "Searchable Recipe",
        "total_servings": 1,
        "ingredients": [{"food_id": ing_id, "quantity": 1}]
    })

    # Search Scope=Food (Should NOT find recipe)
    res_food = client.get("/api/v1/nutrition/search?query=Searchable&scope=food")
    assert len(res_food.json()) == 0

    # Search Scope=Recipe (Should find)
    res_recipe = client.get("/api/v1/nutrition/search?query=Searchable&scope=recipe")
    assert len(res_recipe.json()) == 1
    assert res_recipe.json()[0]["food_name"] == "Searchable Recipe"
