from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from app import database, models, schemas, auth, services

router = APIRouter(
    prefix="/api/v1/log",
    tags=["health"]
)

@router.post("/bp", response_model=schemas.BloodPressureResponse)
def log_blood_pressure(
    bp: schemas.BloodPressureCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    payload = schemas.BPPayload(**bp.dict())
    return service.log_bp(db, current_user.user_id, payload)

@router.post("/exercise")
def log_exercise(
    exercise: schemas.ExercisePayload,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    log = service.log_exercise(db, current_user, exercise)
    return {"message": "Exercise logged", "calories_burned": log.total_calories_burned}

@router.get("/history/exercise")
def get_exercise_history(
    limit: int = 50,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    history = db.query(models.ExerciseLog).filter(
        models.ExerciseLog.user_id == current_user.user_id
    ).order_by(models.ExerciseLog.timestamp.desc()).limit(limit).all()
    return history

@router.get("/summary")
def get_daily_summary(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    today = date.today()

    # 1. Daily Log (Calories In/Out)
    daily = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.user_id,
        models.DailyLog.date == today
    ).first()

    calories_consumed = daily.total_calories_consumed if daily else 0
    calories_burned = daily.total_calories_burned if daily else 0

    # 2. Latest BP
    bp = db.query(models.BloodPressure).filter(
        models.BloodPressure.user_id == current_user.user_id
    ).order_by(models.BloodPressure.timestamp.desc()).first()

    bp_str = f"{bp.systolic}/{bp.diastolic}" if bp else "Not Logged"

    # 3. Macro Calculation (Protein/Fat/Carbs)
    start_of_day = datetime.combine(today, datetime.min.time())
    food_logs = db.query(models.FoodItemLog).join(models.NutritionCache).filter(
        models.FoodItemLog.user_id == current_user.user_id,
        models.FoodItemLog.timestamp >= start_of_day
    ).all()

    macros = {"protein": 0, "fat": 0, "carbs": 0}
    for log in food_logs:
        multiplier = log.serving_size * log.quantity
        # Assuming values in cache are numeric
        macros["protein"] += (log.nutrition_info.protein or 0) * multiplier
        macros["fat"] += (log.nutrition_info.fat or 0) * multiplier
        macros["carbs"] += (log.nutrition_info.carbs or 0) * multiplier

    return {
        "blood_pressure": bp_str,
        "calories_consumed": calories_consumed,
        "calories_burned": calories_burned,
        "macros": macros
    }

@router.get("/reports/adherence")
def get_adherence(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    logs = db.query(models.MedDoseLog).filter(models.MedDoseLog.user_id == current_user.user_id).all()
    total_doses = len(logs)
    return {"total_doses_logged": total_doses}
