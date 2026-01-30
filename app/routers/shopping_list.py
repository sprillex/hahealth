from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import database, models, schemas_shopping, auth

router = APIRouter(
    prefix="/api/v1/shopping-list",
    tags=["shopping-list"]
)

@router.post("/items")
def add_shopping_item(
    item: schemas_shopping.ShoppingListItem,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Adds an existing food item to the shopping list by name.
    If multiple items match the name, it adds the first one found.
    Case-insensitive search.
    """
    food = db.query(models.NutritionCache).filter(
        models.NutritionCache.food_name.ilike(item.name)
    ).first()

    if not food:
        raise HTTPException(status_code=404, detail=f"Food item '{item.name}' not found.")

    food.on_shopping_list = True
    db.commit()
    return {"status": "success", "message": f"Added '{food.food_name}' to shopping list."}

@router.delete("/items")
def remove_shopping_item(
    item: schemas_shopping.ShoppingListItem,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Removes a food item from the shopping list by name.
    Case-insensitive search.
    """
    food = db.query(models.NutritionCache).filter(
        models.NutritionCache.food_name.ilike(item.name)
    ).first()

    if not food:
        raise HTTPException(status_code=404, detail=f"Food item '{item.name}' not found.")

    food.on_shopping_list = False
    db.commit()
    return {"status": "success", "message": f"Removed '{food.food_name}' from shopping list."}
