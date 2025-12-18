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
    # The return value log is a DailyLog object which only has date and total_cals.
    # The caller expects calories burned.
    # In services.py log_exercise returns the DailyLog.
    # It also creates an ExerciseLog.
    # The DailyLog has total_calories_burned updated.
    return {"message": "Exercise logged", "calories_burned": exercise.calories_burned or 0} # Approximate or need to fetch details

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

    # Attach timezone info (SQLite stores as naive UTC)
    for ex in history:
        if ex.timestamp and ex.timestamp.tzinfo is None:
            ex.timestamp = ex.timestamp.replace(tzinfo=timezone.utc)

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

    # Determine UTC range for the User's Local Day
    import zoneinfo
    try:
        user_tz = zoneinfo.ZoneInfo(current_user.timezone) if current_user.timezone else timezone.utc
    except Exception:
        user_tz = timezone.utc

    # Local day start/end
    # Using naive combine and then attaching timezone
    local_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=user_tz)
    local_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=user_tz)

    # Convert to UTC for DB Query
    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)

    bp = db.query(models.BloodPressure).filter(
        models.BloodPressure.user_id == current_user.user_id,
        models.BloodPressure.timestamp >= utc_start,
        models.BloodPressure.timestamp <= utc_end
    ).order_by(models.BloodPressure.timestamp.desc()).first()

    bp_str = f"{bp.systolic}/{bp.diastolic}" if bp else "Not Logged"

    # 3. Macro Calculation (Protein/Fat/Carbs/Fiber)
    food_logs = db.query(models.FoodItemLog).join(models.NutritionCache).filter(
        models.FoodItemLog.user_id == current_user.user_id,
        models.FoodItemLog.timestamp >= utc_start,
        models.FoodItemLog.timestamp <= utc_end
    ).all()

    macros = {"protein": 0, "fat": 0, "carbs": 0, "fiber": 0}
    food_list = []
    for log in food_logs:
        multiplier = log.serving_size * log.quantity
        macros["protein"] += (log.nutrition_info.protein or 0) * multiplier
        macros["fat"] += (log.nutrition_info.fat or 0) * multiplier
        macros["carbs"] += (log.nutrition_info.carbs or 0) * multiplier
        macros["fiber"] += (log.nutrition_info.fiber or 0) * multiplier

        food_list.append({
            "name": log.nutrition_info.food_name,
            "calories": (log.nutrition_info.calories or 0) * multiplier,
            "meal": log.meal_id
        })

    # Fetch Exercises for Today
    exercises_list = []
    daily_exercises = db.query(models.ExerciseLog).filter(
        models.ExerciseLog.user_id == current_user.user_id,
        models.ExerciseLog.timestamp >= utc_start,
        models.ExerciseLog.timestamp <= utc_end
    ).order_by(models.ExerciseLog.timestamp.desc()).all()

    for ex in daily_exercises:
        exercises_list.append({
            "activity": ex.activity_type,
            "duration": ex.duration_minutes,
            "calories": ex.calories_burned
        })

    return {
        "blood_pressure": bp_str,
        "calories_consumed": calories_consumed,
        "calories_burned": calories_burned,
        "macros": macros,
        "food_logs": food_list,
        "exercises": exercises_list
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
