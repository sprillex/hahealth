from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timedelta
from app import database, models, schemas, auth, services

router = APIRouter(
    prefix="/api/v1/log",
    tags=["health"]
)

from datetime import timezone

@router.post("/bp", response_model=schemas.BloodPressureResponse)
def log_blood_pressure(
    bp: schemas.BloodPressureCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    payload = schemas.BPPayload(**bp.dict())
    result = service.log_bp(db, current_user.user_id, payload)
    # Ensure timezone is attached for Pydantic serialization
    if result.timestamp and result.timestamp.tzinfo is None:
        result.timestamp = result.timestamp.replace(tzinfo=timezone.utc)
    return result

@router.post("/exercise")
def log_exercise(
    exercise: schemas.ExercisePayload,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    log = service.log_exercise(db, current_user, exercise)
    return {"message": "Exercise logged", "calories_burned": log.total_calories_burned}

@router.get("/history/bp")
def get_bp_history(
    limit: int = 50,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    history = db.query(models.BloodPressure).filter(
        models.BloodPressure.user_id == current_user.user_id
    ).order_by(models.BloodPressure.timestamp.desc()).limit(limit).all()

    # Attach timezone info (SQLite stores as naive UTC)
    for bp in history:
        if bp.timestamp and bp.timestamp.tzinfo is None:
            bp.timestamp = bp.timestamp.replace(tzinfo=timezone.utc)

    return history

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
    date_str: Optional[str] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date.today()

    # 1. Daily Log (Calories In/Out)
    daily = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.user_id,
        models.DailyLog.date == target_date
    ).first()

    calories_consumed = daily.total_calories_consumed if daily else 0
    calories_burned = daily.total_calories_burned if daily else 0

    # 2. Latest BP (for that day? Or just latest ever? Usually "Summary" implies current status,
    # but if looking back, maybe we want "Latest on that day" or "Average on that day"?)
    # The requirement is "previous days summary's".
    # Showing "Latest BP ever" on a summary for last week is misleading.
    # Let's show "Last BP of that day".

    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    bp = db.query(models.BloodPressure).filter(
        models.BloodPressure.user_id == current_user.user_id,
        models.BloodPressure.timestamp >= start_of_day,
        models.BloodPressure.timestamp <= end_of_day
    ).order_by(models.BloodPressure.timestamp.desc()).first()

    bp_str = f"{bp.systolic}/{bp.diastolic}" if bp else "Not Logged"

    # 3. Macro Calculation (Protein/Fat/Carbs/Fiber)
    food_logs = db.query(models.FoodItemLog).join(models.NutritionCache).filter(
        models.FoodItemLog.user_id == current_user.user_id,
        models.FoodItemLog.timestamp >= start_of_day,
        models.FoodItemLog.timestamp <= end_of_day
    ).all()

    macros = {"protein": 0, "fat": 0, "carbs": 0, "fiber": 0}
    for log in food_logs:
        multiplier = log.serving_size * log.quantity
        # Assuming values in cache are numeric and defaults are 0
        macros["protein"] += (log.nutrition_info.protein or 0) * multiplier
        macros["fat"] += (log.nutrition_info.fat or 0) * multiplier
        macros["carbs"] += (log.nutrition_info.carbs or 0) * multiplier
        macros["fiber"] += (log.nutrition_info.fiber or 0) * multiplier

    return {
        "blood_pressure": bp_str,
        "calories_consumed": calories_consumed,
        "calories_burned": calories_burned,
        "macros": macros
    }

@router.get("/reports/compliance")
def get_compliance(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    report = service.calculate_compliance_report(db, current_user)
    return report

@router.get("/reports/adherence")
def get_adherence(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Deprecated/Simple version kept for backward compatibility if needed,
    # but compliance report is better.
    logs = db.query(models.MedDoseLog).filter(models.MedDoseLog.user_id == current_user.user_id).all()
    total_doses = len(logs)
    return {"total_doses_logged": total_doses}
