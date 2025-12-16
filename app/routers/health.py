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
    # Need to convert Create to Payload or just pass data
    payload = schemas.BPPayload(**bp.dict())
    return service.log_bp(db, current_user.user_id, payload)

@router.get("/reports/adherence")
def get_adherence(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    # Simplified adherence report
    logs = db.query(models.MedDoseLog).filter(models.MedDoseLog.user_id == current_user.user_id).all()
    total_doses = len(logs)
    # This is a very basic placeholder. Real adherence needs schedule vs actual.
    return {"total_doses_logged": total_doses}
