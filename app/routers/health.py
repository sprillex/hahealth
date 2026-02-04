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
    payload = schemas.BPPayload(**bp.model_dump())
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
    return {"message": "Exercise logged", "calories_burned": log.calories_burned}

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

    service = services.HealthLogService()
    return service.get_daily_summary_data(db, current_user, target_date)

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

# --- Management Endpoints ---

@router.delete("/exercise/{log_id}")
def delete_exercise(
    log_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    success = service.delete_exercise_log(db, log_id, current_user.user_id)
    if not success:
         raise HTTPException(status_code=404, detail="Log not found")
    return {"status": "success"}

@router.put("/exercise/{log_id}", response_model=schemas.ExerciseLogResponse)
def update_exercise(
    log_id: int,
    updates: schemas.LogUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    log = service.update_exercise_log(db, log_id, current_user.user_id, updates)
    if not log:
         raise HTTPException(status_code=404, detail="Log not found")

    ts = log.timestamp
    if ts and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return {
        "log_id": log.exercise_id,
        "activity_type": log.activity_type,
        "duration_minutes": log.duration_minutes,
        "calories_burned": log.calories_burned,
        "timestamp": ts
    }

@router.delete("/food/{log_id}")
def delete_food(
    log_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    success = service.delete_food_log(db, log_id, current_user.user_id)
    if not success:
         raise HTTPException(status_code=404, detail="Log not found")
    return {"status": "success"}

@router.put("/food/{log_id}", response_model=schemas.FoodLogResponse)
def update_food(
    log_id: int,
    updates: schemas.LogUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    service = services.HealthLogService()
    log = service.update_food_log(db, log_id, current_user.user_id, updates)
    if not log:
         raise HTTPException(status_code=404, detail="Log not found")

    # Calculate calories for response
    cals = log.nutrition_info.calories * log.serving_size * log.quantity

    ts = log.timestamp
    if ts and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return {
        "log_id": log.item_log_id,
        "food_name": log.nutrition_info.food_name,
        "meal_id": log.meal_id,
        "calories": cals,
        "serving_size": log.serving_size,
        "quantity": log.quantity,
        "planned_quantity": log.planned_quantity,
        "timestamp": ts
    }
