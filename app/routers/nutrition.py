from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app import database, models, schemas, auth, services

router = APIRouter(
    prefix="/api/v1/nutrition",
    tags=["nutrition"]
)

@router.post("/", response_model=schemas.NutritionCacheResponse)
def create_custom_food(
    food: schemas.NutritionCacheCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Check if exists (by barcode if provided, or name)
    if food.barcode:
        exists = db.query(models.NutritionCache).filter(models.NutritionCache.barcode == food.barcode).first()
        if exists:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    # If no barcode, ensure unique name?
    # Or just allow duplicates? Best to warn if exact name exists.
    # But user might want to create "Apple" manually if OFF failed.

    new_food = models.NutritionCache(
        barcode=food.barcode,
        food_name=food.food_name,
        calories=food.calories,
        protein=food.protein,
        fat=food.fat,
        carbs=food.carbs,
        fiber=food.fiber,
        source="MANUAL"
    )
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

@router.get("/search", response_model=List[schemas.NutritionCacheResponse])
def search_food(
    query: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Simple search
    results = db.query(models.NutritionCache).filter(
        models.NutritionCache.food_name.ilike(f"%{query}%")
    ).limit(20).all()
    return results

@router.post("/log", response_model=schemas.FoodLogPayload) # Return type might need adjustment
def log_food_entry(
    entry: schemas.FoodLogPayload,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    item, error = service.log_food(db, current_user, entry)
    if error:
        raise HTTPException(status_code=404, detail=error)

    # Construct response
    return entry
