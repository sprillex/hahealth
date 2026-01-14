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
        sodium=food.sodium,
        source="MANUAL"
    )
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

@router.get("/search", response_model=List[schemas.NutritionCacheResponse])
def search_food(
    query: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    results = []

    # If no query, return recent or all (limit 50)
    if not query:
        return db.query(models.NutritionCache).filter(
            models.NutritionCache.is_user_visible == True
        ).limit(50).all()

    # Check if query looks like a barcode
    if query.isdigit() and len(query) > 3:
        service = services.OpenFoodFactsService()
        product = service.get_product(query, db)
        if product:
            results.append(product)
            return results

    # Name search fallback
    name_results = db.query(models.NutritionCache).filter(
        models.NutritionCache.food_name.ilike(f"%{query}%"),
        models.NutritionCache.is_user_visible == True
    ).limit(20).all()

    results.extend(name_results)

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

@router.get("/list", response_model=List[schemas.NutritionCacheResponse])
def list_foods(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    include_hidden: bool = False,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    query = db.query(models.NutritionCache)
    if search:
        query = query.filter(models.NutritionCache.food_name.ilike(f"%{search}%"))

    if not include_hidden:
        query = query.filter(models.NutritionCache.is_user_visible == True)

    return query.offset(skip).limit(limit).all()

@router.get("/{food_id}", response_model=schemas.NutritionCacheResponse)
def get_food(
    food_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

@router.put("/{food_id}", response_model=schemas.NutritionCacheResponse)
def update_food(
    food_id: int,
    updates: schemas.NutritionCacheUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(food, key, value)

    db.commit()
    db.refresh(food)
    return food

@router.delete("/{food_id}")
def delete_food(
    food_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Check usage first
    usage = db.query(models.FoodItemLog).filter(models.FoodItemLog.food_id == food_id).first()
    if usage:
        # We can't easily delete because logs depend on it.
        # Options:
        # 1. Block delete (Safest)
        # 2. Hide it (is_user_visible=False) - but endpoint says DELETE.
        # Let's block it for now with a clear message.
        raise HTTPException(status_code=400, detail="Cannot delete food that is used in logs. Please hide it instead or delete logs first.")

    food = db.query(models.NutritionCache).filter(models.NutritionCache.food_id == food_id).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")

    db.delete(food)
    db.commit()
    return {"status": "success"}
