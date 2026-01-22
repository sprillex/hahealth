from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app import database, models, schemas, auth, services
from datetime import datetime, timezone

router = APIRouter(
    prefix="/api/v1/nutrition",
    tags=["nutrition"]
)

router_v2 = APIRouter(
    prefix="/api/v2/nutrition",
    tags=["nutrition_v2"]
)

@router.post("/", response_model=schemas.NutritionCacheResponse)
def create_custom_food(
    food: schemas.NutritionCacheCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Check if exists (by barcode if provided, or name)
    if food.barcode:
        service = services.CustomNutritionService()
        exists = service.find_in_cache(db, food.barcode)
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
        # New fields defaults
        brand=food.brand,
        serving_size_unit=food.serving_size_unit,
        cholesterol=food.cholesterol,
        total_sugars=food.total_sugars,
        added_sugars=food.added_sugars,
        vitamin_d=food.vitamin_d,
        calcium=food.calcium,
        iron=food.iron,
        potassium=food.potassium,
        health_score=food.health_score,
        health_insight=food.health_insight,
        pairing_tip=food.pairing_tip,
        source="MANUAL"
    )
    db.add(new_food)
    db.commit()
    db.refresh(new_food)
    return new_food

@router.get("/search", response_model=List[schemas.NutritionCacheResponse])
def search_food(
    query: Optional[str] = None,
    scope: str = "food", # food, recipe
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    results = []

    # Base query for source filtering
    base_query = db.query(models.NutritionCache).filter(
        models.NutritionCache.is_user_visible == True
    )

    if scope == "recipe":
        base_query = base_query.filter(models.NutritionCache.source == "RECIPE")
    else:
        # Exclude recipes if scope is food
        base_query = base_query.filter(models.NutritionCache.source != "RECIPE")

    # If no query, return recent or all (limit 50)
    if not query:
        return base_query.limit(50).all()

    # Check if query looks like a barcode (Only for foods)
    if scope != "recipe" and query.isdigit() and len(query) > 3:
        service = services.CustomNutritionService()
        product = service.get_product(query, db)
        if product:
            results.append(product)
            return results

    # Name search fallback
    name_results = base_query.filter(
        models.NutritionCache.food_name.ilike(f"%{query}%")
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

# V2 Implementation

def _convert_to_v2_schema(food: models.NutritionCache) -> schemas.V2FoodItem:
    return schemas.V2FoodItem(
        metadata=schemas.V2Metadata(
            name=food.food_name,
            brand=food.brand,
            upc=food.barcode,
            srv_per_cont=None # Not stored in cache currently
        ),
        macros=schemas.V2Macros(
            calories=food.calories,
            protein_g=food.protein,
            fat_g=food.fat,
            carbs_g=food.carbs,
            fiber_g=food.fiber,
            sodium_mg=food.sodium,
            cholesterol_mg=food.cholesterol,
            total_sugars_g=food.total_sugars,
            added_sugars_g=food.added_sugars
        ),
        micros=schemas.V2Micros(
            vit_d_mcg=food.vitamin_d,
            calcium_mg=food.calcium,
            iron_mg=food.iron,
            potassium_mg=food.potassium
        ),
        serving_info=schemas.V2ServingInfo(
            size=food.serving_size_unit
        ),
        analysis=schemas.V2Analysis(
            score_color=food.health_score,
            health_insight=food.health_insight,
            pairing_tip=food.pairing_tip
        )
    )

@router_v2.get("/lookup/{barcode}", response_model=schemas.V2FoodItem)
def lookup_food_v2(
    barcode: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # 1. Check Local DB
    service = services.CustomNutritionService()
    cached = service.find_in_cache(db, barcode)
    if cached:
        return _convert_to_v2_schema(cached)

    # 2. Fetch Remote (Do not save)
    fetched = service._fetch_remote_product(barcode)

    if fetched:
        return _convert_to_v2_schema(fetched)

    raise HTTPException(status_code=404, detail="Food not found")

@router_v2.post("/log", response_model=schemas.FoodLogResponse)
def log_food_v2(
    payload: schemas.NutritionLogV2,
    check_existence: bool = False,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # 1. Extract Food Data
    if not payload.variables:
         raise HTTPException(status_code=400, detail="No food variables provided")

    # Take the first key
    food_name_key = next(iter(payload.variables))
    food_data = payload.variables[food_name_key]

    # Resolve Name: use metadata.name if present, else key
    final_name = food_data.metadata.name or food_name_key

    # 2. Check existence
    # Try UPC
    food_item = None
    if food_data.metadata.upc:
        service = services.CustomNutritionService()
        food_item = service.find_in_cache(db, food_data.metadata.upc)

    # Try Name
    if not food_item:
        food_item = db.query(models.NutritionCache).filter(models.NutritionCache.food_name == final_name).first()

    if check_existence:
        if food_item:
            return JSONResponse(status_code=409, content={"detail": "Food already exists", "food_name": food_item.food_name})
        else:
            return JSONResponse(status_code=200, content={"detail": "Food available"})

    # 3. Prepare Attributes
    def sf(val): return val if val is not None else 0.0

    attrs = {
        "food_name": final_name,
        "barcode": food_data.metadata.upc,
        "brand": food_data.metadata.brand,
        "serving_size_unit": food_data.serving_info.size if food_data.serving_info else None,

        # Base Macros
        "calories": sf(food_data.macros.calories),
        "protein": sf(food_data.macros.protein_g),
        "fat": sf(food_data.macros.fat_g),
        "carbs": sf(food_data.macros.carbs_g),
        "fiber": sf(food_data.macros.fiber_g),
        "sodium": sf(food_data.macros.sodium_mg),

        # Extended
        "cholesterol": sf(food_data.macros.cholesterol_mg),
        "total_sugars": sf(food_data.macros.total_sugars_g),
        "added_sugars": sf(food_data.macros.added_sugars_g),

        # Micros
        "vitamin_d": sf(food_data.micros.vit_d_mcg) if food_data.micros else 0.0,
        "calcium": sf(food_data.micros.calcium_mg) if food_data.micros else 0.0,
        "iron": sf(food_data.micros.iron_mg) if food_data.micros else 0.0,
        "potassium": sf(food_data.micros.potassium_mg) if food_data.micros else 0.0,

        # Analysis
        "health_score": food_data.analysis.score_color if food_data.analysis else None,
        "health_insight": food_data.analysis.health_insight if food_data.analysis else None,
        "pairing_tip": food_data.analysis.pairing_tip if food_data.analysis else None,

        "source": "MANUAL",
        "is_user_visible": True
    }

    if food_item:
        # Update
        for k, v in attrs.items():
            setattr(food_item, k, v)
    else:
        # Create
        food_item = models.NutritionCache(**attrs)
        db.add(food_item)

    db.commit()
    db.refresh(food_item)

    # 4. Create Log if quantity > 0
    if payload.quantity > 0:
        ts = payload.timestamp
        if not ts:
            ts = datetime.now(timezone.utc)
        else:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

        item_log = models.FoodItemLog(
            user_id=current_user.user_id,
            meal_id=payload.meal,
            food_id=food_item.food_id,
            serving_size=1.0,
            quantity=payload.quantity,
            timestamp=ts
        )
        db.add(item_log)

        # Update Daily Log
        local_date = services.get_user_local_date(current_user, ts)
        daily_log = db.query(models.DailyLog).filter(models.DailyLog.user_id == current_user.user_id, models.DailyLog.date == local_date).first()
        if not daily_log:
            daily_log = models.DailyLog(user_id=current_user.user_id, date=local_date, total_calories_burned=0, total_calories_consumed=0)
            db.add(daily_log)

        total_cals = food_item.calories * item_log.quantity
        daily_log.total_calories_consumed += total_cals

        db.commit()
        db.refresh(item_log)

        return schemas.FoodLogResponse(
            log_id=item_log.item_log_id,
            food_name=food_item.food_name,
            meal_id=item_log.meal_id,
            calories=total_cals,
            serving_size=item_log.serving_size,
            quantity=item_log.quantity,
            timestamp=item_log.timestamp
        )
    else:
        # Save Only
        return schemas.FoodLogResponse(
            log_id=None,
            food_name=food_item.food_name,
            meal_id=payload.meal,
            calories=0.0,
            serving_size=1.0,
            quantity=0.0,
            timestamp=None
        )
