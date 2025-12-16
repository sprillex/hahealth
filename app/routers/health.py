from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
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
    # Return DailyLog, but maybe we want to return the exercise entry?
    # For now, sticking to previous contract but logic is updated.
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

@router.get("/reports/adherence")
def get_adherence(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    logs = db.query(models.MedDoseLog).filter(models.MedDoseLog.user_id == current_user.user_id).all()
    total_doses = len(logs)
    return {"total_doses_logged": total_doses}
