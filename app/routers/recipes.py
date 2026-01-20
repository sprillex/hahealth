from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app import database, models, schemas, auth
import datetime
from datetime import timezone

router = APIRouter(
    prefix="/api/v1/recipes",
    tags=["recipes"]
)

def calculate_recipe_nutrition(db: Session, ingredients: List[schemas.RecipeIngredientCreate], total_servings: float):
    total_cals = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    total_fiber = 0.0
    total_sodium = 0.0

    # Extended totals
    total_cholesterol = 0.0
    total_sugars = 0.0
    total_added_sugars = 0.0
    total_vit_d = 0.0
    total_calcium = 0.0
    total_iron = 0.0
    total_potassium = 0.0

    for ing in ingredients:
        food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == ing.food_id).first()
        if not food:
            raise HTTPException(status_code=400, detail=f"Ingredient food_id {ing.food_id} not found")

        q = ing.quantity
        total_cals += food.calories * q
        total_protein += food.protein * q
        total_fat += food.fat * q
        total_carbs += food.carbs * q
        total_fiber += food.fiber * q
        total_sodium += (food.sodium or 0.0) * q

        total_cholesterol += (food.cholesterol or 0.0) * q
        total_sugars += (food.total_sugars or 0.0) * q
        total_added_sugars += (food.added_sugars or 0.0) * q
        total_vit_d += (food.vitamin_d or 0.0) * q
        total_calcium += (food.calcium or 0.0) * q
        total_iron += (food.iron or 0.0) * q
        total_potassium += (food.potassium or 0.0) * q

    if total_servings <= 0:
        total_servings = 1.0

    return {
        "calories": total_cals / total_servings,
        "protein": total_protein / total_servings,
        "fat": total_fat / total_servings,
        "carbs": total_carbs / total_servings,
        "fiber": total_fiber / total_servings,
        "sodium": total_sodium / total_servings,
        "cholesterol": total_cholesterol / total_servings,
        "total_sugars": total_sugars / total_servings,
        "added_sugars": total_added_sugars / total_servings,
        "vitamin_d": total_vit_d / total_servings,
        "calcium": total_calcium / total_servings,
        "iron": total_iron / total_servings,
        "potassium": total_potassium / total_servings,
    }

@router.post("/", response_model=schemas.RecipeResponse)
def create_recipe(
    recipe: schemas.RecipeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # 1. Calculate Nutrition
    macros = calculate_recipe_nutrition(db, recipe.ingredients, recipe.total_servings)

    # 2. Create NutritionCache Entry
    cache_entry = models.NutritionCache(
        food_name=recipe.name,
        calories=macros["calories"],
        protein=macros["protein"],
        fat=macros["fat"],
        carbs=macros["carbs"],
        fiber=macros["fiber"],
        sodium=macros["sodium"],
        cholesterol=macros["cholesterol"],
        total_sugars=macros["total_sugars"],
        added_sugars=macros["added_sugars"],
        vitamin_d=macros["vitamin_d"],
        calcium=macros["calcium"],
        iron=macros["iron"],
        potassium=macros["potassium"],

        brand="Home Recipe",
        serving_size_unit="1 serving",

        health_score=recipe.health_score,
        health_insight=recipe.health_insight,
        pairing_tip=recipe.pairing_tip,

        source="RECIPE",
        is_user_visible=True
    )
    db.add(cache_entry)
    db.commit()
    db.refresh(cache_entry)

    # 3. Create Recipe
    new_recipe = models.Recipe(
        user_id=current_user.user_id,
        name=recipe.name,
        instructions=recipe.instructions,
        cook_time_minutes=recipe.cook_time_minutes,
        prep_time_minutes=recipe.prep_time_minutes,
        total_servings=recipe.total_servings,
        current_food_id=cache_entry.food_id
    )
    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)

    # 4. Create Ingredients
    for ing in recipe.ingredients:
        ri = models.RecipeIngredient(
            recipe_id=new_recipe.recipe_id,
            food_id=ing.food_id,
            quantity=ing.quantity
        )
        db.add(ri)

    db.commit()
    db.refresh(new_recipe)
    return new_recipe

@router.get("/", response_model=List[schemas.RecipeResponse])
def list_recipes(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Recipe).filter(models.Recipe.user_id == current_user.user_id).all()

@router.get("/{recipe_id}", response_model=schemas.RecipeResponse)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    recipe = db.query(models.Recipe).filter(
        models.Recipe.recipe_id == recipe_id,
        models.Recipe.user_id == current_user.user_id
    ).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

@router.put("/{recipe_id}", response_model=schemas.RecipeResponse)
def update_recipe(
    recipe_id: int,
    updates: schemas.RecipeUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    recipe = db.query(models.Recipe).filter(
        models.Recipe.recipe_id == recipe_id,
        models.Recipe.user_id == current_user.user_id
    ).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    recalc_needed = False
    if updates.ingredients is not None or updates.total_servings is not None:
        recalc_needed = True

    # Update Fields
    if updates.name: recipe.name = updates.name
    if updates.instructions is not None: recipe.instructions = updates.instructions
    if updates.cook_time_minutes is not None: recipe.cook_time_minutes = updates.cook_time_minutes
    if updates.prep_time_minutes is not None: recipe.prep_time_minutes = updates.prep_time_minutes

    if recalc_needed:
        new_servings = updates.total_servings if updates.total_servings is not None else recipe.total_servings

        ingredients_to_use = []
        if updates.ingredients is not None:
            ingredients_to_use = updates.ingredients
        else:
            for ri in recipe.ingredients:
                ingredients_to_use.append(schemas.RecipeIngredientCreate(food_id=ri.food_id, quantity=ri.quantity))

        macros = calculate_recipe_nutrition(db, ingredients_to_use, new_servings)

        usage = db.query(models.FoodItemLog).filter(models.FoodItemLog.food_id == recipe.current_food_id).first()

        old_food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == recipe.current_food_id).first()

        if usage:
            # Hide old
            if old_food:
                old_food.is_user_visible = False

            # Create NEW
            new_food = models.NutritionCache(
                food_name=recipe.name,
                source="RECIPE",
                is_user_visible=True,
                brand="Home Recipe",
                serving_size_unit="1 serving",
                calories=macros["calories"],
                protein=macros["protein"],
                fat=macros["fat"],
                carbs=macros["carbs"],
                fiber=macros["fiber"],
                sodium=macros["sodium"],
                cholesterol=macros["cholesterol"],
                total_sugars=macros["total_sugars"],
                added_sugars=macros["added_sugars"],
                vitamin_d=macros["vitamin_d"],
                calcium=macros["calcium"],
                iron=macros["iron"],
                potassium=macros["potassium"],
                # Use updates or fallback to old
                health_score=updates.health_score if updates.health_score is not None else (old_food.health_score if old_food else None),
                health_insight=updates.health_insight if updates.health_insight is not None else (old_food.health_insight if old_food else None),
                pairing_tip=updates.pairing_tip if updates.pairing_tip is not None else (old_food.pairing_tip if old_food else None)
            )
            db.add(new_food)
            db.commit()
            db.refresh(new_food)

            recipe.current_food_id = new_food.food_id

        else:
            # Update in place
            if old_food:
                old_food.food_name = recipe.name
                old_food.calories = macros["calories"]
                old_food.protein = macros["protein"]
                old_food.fat = macros["fat"]
                old_food.carbs = macros["carbs"]
                old_food.fiber = macros["fiber"]
                old_food.sodium = macros["sodium"]
                old_food.cholesterol = macros["cholesterol"]
                old_food.total_sugars = macros["total_sugars"]
                old_food.added_sugars = macros["added_sugars"]
                old_food.vitamin_d = macros["vitamin_d"]
                old_food.calcium = macros["calcium"]
                old_food.iron = macros["iron"]
                old_food.potassium = macros["potassium"]

                if updates.health_score is not None: old_food.health_score = updates.health_score
                if updates.health_insight is not None: old_food.health_insight = updates.health_insight
                if updates.pairing_tip is not None: old_food.pairing_tip = updates.pairing_tip

                db.add(old_food)

        recipe.total_servings = new_servings

        if updates.ingredients is not None:
            db.query(models.RecipeIngredient).filter(models.RecipeIngredient.recipe_id == recipe_id).delete()
            for ing in updates.ingredients:
                ri = models.RecipeIngredient(
                    recipe_id=recipe_id,
                    food_id=ing.food_id,
                    quantity=ing.quantity
                )
                db.add(ri)

    else:
        # Just metadata
        if updates.name or updates.health_score is not None or updates.health_insight is not None or updates.pairing_tip is not None:
             food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == recipe.current_food_id).first()
             if food:
                 if updates.name: food.food_name = updates.name
                 if updates.health_score is not None: food.health_score = updates.health_score
                 if updates.health_insight is not None: food.health_insight = updates.health_insight
                 if updates.pairing_tip is not None: food.pairing_tip = updates.pairing_tip
                 db.add(food)

    db.commit()
    db.refresh(recipe)
    return recipe

@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    recipe = db.query(models.Recipe).filter(
        models.Recipe.recipe_id == recipe_id,
        models.Recipe.user_id == current_user.user_id
    ).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    usage = db.query(models.FoodItemLog).filter(models.FoodItemLog.food_id == recipe.current_food_id).first()
    food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == recipe.current_food_id).first()

    if usage:
        if food:
            food.is_user_visible = False
            db.add(food)
    else:
        if food:
            db.delete(food)

    db.delete(recipe)
    db.commit()
    return {"status": "success"}
